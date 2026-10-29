#!/usr/bin/env python3
"""Seed idempotent managed ERP showcase data through native Odoo models.

Run with:
  docker exec -i erp-local-app python /opt/odoo/odoo-bin shell \
    --db_host=erp-local-db --db_port=5432 --db_user=odoo --db_password=odoo \
    -d erp_local --no-http < scripts/seed_managed_demo.py
"""

from datetime import date, timedelta

from odoo import Command, fields


if env.cr.dbname != 'erp_local' and not env.cr.dbname.startswith('test_'):
    raise RuntimeError(f'Refusing to seed non-development database: {env.cr.dbname}')

MODULE = 'managed_demo'
Data = env['ir.model.data'].sudo()


def existing(name):
    data = Data.search([('module', '=', MODULE), ('name', '=', name)], limit=1)
    return env[data.model].browse(data.res_id).exists() if data else False


def remember(name, record):
    if not Data.search_count([('module', '=', MODULE), ('name', '=', name)]):
        Data.create({'module': MODULE, 'name': name, 'model': record._name, 'res_id': record.id, 'noupdate': True})
    return record


def ensure(name, model, values, context=None, fallback_domain=None):
    record = existing(name)
    if not record and fallback_domain:
        record = env[model].with_context(active_test=False).search(fallback_domain, limit=1)
    if not record:
        record = env[model].with_context(**(context or {})).create(values)
    return remember(name, record)


def ensure_role(partner, role):
    partner._ensure_managed_role(role)
    return partner


def ensure_address(name, account, values):
    return ensure(name, 'managed.partner.address', {'account_id': account.id, **values})


def ensure_product_category(name, label, parent=None):
    return ensure(name, 'product.category', {'name': label, 'parent_id': parent.id if parent else False}, context={'managed_ui': True})


def ensure_attribute(name, label, value_specs):
    attribute = ensure(name, 'product.attribute', {
        'name': label, 'display_type': 'pills', 'create_variant': 'always',
    }, context={'managed_ui': True})
    values = []
    for key, value_label in value_specs:
        values.append(ensure(f'{name}_{key}', 'product.attribute.value', {
            'name': value_label, 'attribute_id': attribute.id,
        }, context={'managed_ui': True}))
    return attribute, env['product.attribute.value'].concat(*values)


def set_variant_identity(template, identities):
    for variant in template.product_variant_ids:
        identity = identities.get(variant.managed_variant_name)
        if identity:
            variant.with_context(managed_ui=True).write({'default_code': identity[0], 'barcode': identity[1]})


def set_value_extras(template, extras):
    for value in template.attribute_line_ids.product_template_value_ids:
        label = value.product_attribute_value_id.name
        if label in extras:
            value.price_extra = extras[label]


def ensure_order(name, values, state='draft'):
    order = existing(name)
    if order:
        return order
    order = remember(name, env['sale.order'].with_context(managed_ui=True).create(values))
    if state == 'sent':
        order.action_quotation_sent()
    elif state == 'sale':
        order.action_confirm()
    order.message_post(body='Data demo managed ERP untuk preview alur penjualan.')
    return order

def ensure_purchase_order(name, values, confirm=False):
    order = existing(name)
    if order:
        return order
    order = remember(name, env['purchase.order'].create(values))
    if confirm:
        order.button_confirm()
    return order

def validate_picking(picking):
    picking.action_assign()
    for line in picking.move_line_ids_without_package:
        line.qty_done = line.reserved_uom_qty or line.product_uom_qty
    result = picking.button_validate()
    if isinstance(result, dict) and result.get('res_model') in ('stock.immediate.transfer', 'stock.backorder.confirmation'):
        env[result['res_model']].with_context(**result.get('context', {})).create({}).process()
    return picking

def ensure_paid_invoice(name, order, journal):
    invoice = existing(name)
    if invoice:
        return invoice
    invoice = remember(name, order._create_invoices())
    invoice.action_post()
    payment = env['account.payment.register'].with_context(
        active_model='account.move', active_ids=invoice.ids,
    ).create({'journal_id': journal.id, 'amount': invoice.amount_residual})._create_payments()
    remember(f'{name}_payment', payment)
    return invoice


company = env.company
country_id = env.ref('base.id')
if company.name == 'My Company':
    company.write({
        'name': 'Toova Demo Indonesia', 'email': 'hello@toova-demo.test', 'phone': '+62 21 7000 0000',
        'website': 'https://toova-demo.test', 'country_id': country_id.id,
        'street': 'Jl. Teknologi Indonesia No. 1', 'city': 'Jakarta', 'zip': '12950',
    })
state_jakarta = env['res.country.state'].search([('country_id', '=', country_id.id), ('name', 'ilike', 'Jakarta')], limit=1)
state_jabar = env['res.country.state'].search([('country_id', '=', country_id.id), ('name', 'ilike', 'Jawa Barat')], limit=1)
currency = company.currency_id
warehouse = env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
unit = env.ref('uom.product_uom_unit')
kg = env.ref('uom.product_uom_kgm')
sale_tax = env['account.tax'].search([('company_id', '=', company.id), ('type_tax_use', '=', 'sale'), ('active', '=', True)], limit=1)
payment_term = env['account.payment.term'].search([('company_id', 'in', [False, company.id])], limit=1)
bank_journal = env['account.journal'].search([
    ('type', 'in', ('bank', 'cash')), ('company_id', '=', company.id),
], limit=1)

# Directory: customers, vendors, contacts, addresses, bank accounts.
customer_nusantara = ensure_role(ensure('customer_nusantara', 'res.partner', {
    'name': 'PT Nusantara Digital', 'company_type': 'company', 'is_company': True,
    'ref': 'DEMO-CUST-001', 'email': 'sales@nusantara-demo.test', 'phone': '+62 21 555 0101',
    'website': 'https://nusantara-demo.test', 'country_id': country_id.id,
    'state_id': state_jakarta.id, 'city': 'Jakarta Selatan', 'zip': '12190',
    'managed_address_text': 'Jl. Jenderal Sudirman Kav. 10\nGedung Nusantara Lantai 8',
}, context={'managed_ui': True, 'managed_party_role': 'customer'}, fallback_domain=[('ref', '=', 'DEMO-CUST-001')]), 'customer')
customer_cakrawala = ensure_role(ensure('customer_cakrawala', 'res.partner', {
    'name': 'CV Cakrawala Retail', 'company_type': 'company', 'is_company': True,
    'ref': 'DEMO-CUST-002', 'email': 'order@cakrawala-demo.test', 'phone': '+62 22 555 0202',
    'country_id': country_id.id, 'state_id': state_jabar.id, 'city': 'Bandung', 'zip': '40115',
    'managed_address_text': 'Jl. Asia Afrika No. 88',
}, context={'managed_ui': True, 'managed_party_role': 'customer'}, fallback_domain=[('ref', '=', 'DEMO-CUST-002')]), 'customer')
customer_rasa = ensure_role(ensure('customer_rasa', 'res.partner', {
    'name': 'PT Rasa Pangan Indonesia', 'company_type': 'company', 'is_company': True,
    'ref': 'DEMO-CUST-003', 'email': 'procurement@rasa-demo.test', 'phone': '+62 21 555 0303',
    'country_id': country_id.id, 'state_id': state_jakarta.id, 'city': 'Jakarta Timur', 'zip': '13420',
    'managed_address_text': 'Jl. Raya Bekasi KM 18',
}, context={'managed_ui': True, 'managed_party_role': 'customer'}, fallback_domain=[('ref', '=', 'DEMO-CUST-003')]), 'customer')

ensure_address('address_nusantara_invoice', customer_nusantara, {
    'label': 'Kantor pusat', 'recipient_name': 'Finance Nusantara', 'recipient_phone': '+62 21 555 0110',
    'recipient_email': 'finance@nusantara-demo.test', 'managed_address_text': 'Jl. Jenderal Sudirman Kav. 10\nGedung Nusantara Lantai 8',
    'country_id': country_id.id, 'state_id': state_jakarta.id, 'city': 'Jakarta Selatan', 'zip': '12190',
    'use_for_billing': True, 'is_default_billing': True, 'active': True,
})
ensure_address('address_nusantara_shipping', customer_nusantara, {
    'label': 'Gudang Cakung', 'recipient_name': 'Budi Gudang', 'recipient_phone': '+62 812 9000 1001',
    'managed_address_text': 'Kawasan Industri Cakung Blok D-12', 'country_id': country_id.id,
    'state_id': state_jakarta.id, 'city': 'Jakarta Timur', 'zip': '13910',
    'use_for_shipping': True, 'is_default_shipping': True, 'active': True,
})
ensure_address('address_cakrawala_default', customer_cakrawala, {
    'label': 'Toko utama', 'recipient_name': 'Operasional Cakrawala', 'recipient_phone': '+62 812 9000 2002',
    'managed_address_text': 'Jl. Asia Afrika No. 88', 'country_id': country_id.id,
    'state_id': state_jabar.id, 'city': 'Bandung', 'zip': '40115',
    'use_for_billing': True, 'use_for_shipping': True, 'is_default_billing': True, 'is_default_shipping': True, 'active': True,
})

pic_ayu = ensure('contact_ayu', 'res.partner', {
    'name': 'Ayu Prameswari', 'parent_id': customer_nusantara.id, 'type': 'contact', 'function': 'Procurement Manager',
    'email': 'ayu@nusantara-demo.test', 'mobile': '+62 812 1000 1001',
}, context={'managed_ui': True, 'managed_party_role': 'contact'})
pic_dimas = ensure('contact_dimas', 'res.partner', {
    'name': 'Dimas Saputra', 'parent_id': customer_cakrawala.id, 'type': 'contact', 'function': 'Store Manager',
    'email': 'dimas@cakrawala-demo.test', 'mobile': '+62 812 2000 2002',
}, context={'managed_ui': True, 'managed_party_role': 'contact'})
ensure_role(pic_ayu, 'contact')
ensure_role(pic_dimas, 'contact')

vendor_textile = ensure_role(ensure('vendor_textile', 'res.partner', {
    'name': 'PT Tekstil Mandiri', 'company_type': 'company', 'is_company': True, 'ref': 'DEMO-VEND-001',
    'email': 'supply@tekstil-demo.test', 'phone': '+62 22 555 1101', 'country_id': country_id.id,
    'state_id': state_jabar.id, 'city': 'Bandung', 'managed_address_text': 'Jl. Industri Tekstil No. 5',
}, context={'managed_ui': True, 'managed_party_role': 'vendor'}, fallback_domain=[('ref', '=', 'DEMO-VEND-001')]), 'vendor')
vendor_coffee = ensure_role(ensure('vendor_coffee', 'res.partner', {
    'name': 'Koperasi Kopi Gayo', 'company_type': 'company', 'is_company': True, 'ref': 'DEMO-VEND-002',
    'email': 'mitra@kopigayo-demo.test', 'phone': '+62 811 555 2202', 'country_id': country_id.id,
    'city': 'Takengon', 'managed_address_text': 'Jl. Kebun Kopi No. 21',
}, context={'managed_ui': True, 'managed_party_role': 'vendor'}, fallback_domain=[('ref', '=', 'DEMO-VEND-002')]), 'vendor')
ensure('vendor_textile_bank', 'res.partner.bank', {
    'partner_id': vendor_textile.id, 'acc_number': 'DEMO-001-889900', 'acc_holder_name': vendor_textile.name,
    'bank_name': 'Bank Demo Indonesia', 'currency_id': currency.id, 'allow_out_payment': True,
})
ensure('vendor_coffee_bank', 'res.partner.bank', {
    'partner_id': vendor_coffee.id, 'acc_number': 'DEMO-002-778800', 'acc_holder_name': vendor_coffee.name,
    'bank_name': 'Bank Demo Nusantara', 'currency_id': currency.id, 'allow_out_payment': True,
})

# People directory.
department = ensure('department_sales', 'hr.department', {'name': 'Sales & Customer Success', 'company_id': company.id})
job_sales = ensure('job_account_executive', 'hr.job', {'name': 'Account Executive', 'company_id': company.id})
job_ops = ensure('job_sales_operations', 'hr.job', {'name': 'Sales Operations', 'company_id': company.id})
ensure('employee_nadia', 'hr.employee', {
    'name': 'Nadia Putri', 'company_id': company.id, 'department_id': department.id, 'job_id': job_sales.id,
    'work_email': 'nadia@demo.internal', 'work_phone': '+62 21 7000 1001', 'mobile_phone': '+62 812 7000 1001',
})
ensure('employee_rizky', 'hr.employee', {
    'name': 'Rizky Mahendra', 'company_id': company.id, 'department_id': department.id, 'job_id': job_ops.id,
    'work_email': 'rizky@demo.internal', 'work_phone': '+62 21 7000 1002', 'mobile_phone': '+62 812 7000 1002',
})

# Catalog: categories, attributes, variants, supplier prices, stock, and pricelists.
category_demo = ensure_product_category('category_demo', 'Demo Catalog')
category_fashion = ensure_product_category('category_fashion', 'Fashion', category_demo)
category_food = ensure_product_category('category_food', 'Makanan & Minuman', category_demo)
category_service = ensure_product_category('category_service', 'Jasa', category_demo)
size_attribute, size_values = ensure_attribute('attribute_size', 'Ukuran', [('s', 'S'), ('m', 'M'), ('l', 'L')])
pack_attribute, pack_values = ensure_attribute('attribute_pack', 'Isi Kemasan', [('250g', '250 g'), ('500g', '500 g'), ('1kg', '1 kg')])

tax_commands = [Command.set(sale_tax.ids)] if sale_tax else []
shirt = ensure('product_shirt', 'product.template', {
    'name': 'Kaos Nusantara', 'managed_product_kind': 'goods', 'managed_track_inventory': True,
    'sale_ok': True, 'purchase_ok': True, 'categ_id': category_fashion.id, 'uom_id': unit.id, 'uom_po_id': unit.id,
    'list_price': 120000, 'standard_price': 65000, 'taxes_id': tax_commands,
    'description_sale': 'Kaos katun premium produksi lokal.',
    'attribute_line_ids': [Command.create({'attribute_id': size_attribute.id, 'value_ids': [Command.set(size_values.ids)]})],
}, context={'managed_ui': True})
set_value_extras(shirt, {'S': 0, 'M': 10000, 'L': 20000})
set_variant_identity(shirt, {'S': ('KNS-S', '8990000000011'), 'M': ('KNS-M', '8990000000028'), 'L': ('KNS-L', '8990000000035')})

coffee = ensure('product_coffee', 'product.template', {
    'name': 'Kopi Arabika Gayo', 'managed_product_kind': 'goods', 'managed_track_inventory': True,
    'sale_ok': True, 'purchase_ok': True, 'categ_id': category_food.id, 'uom_id': unit.id, 'uom_po_id': unit.id,
    'list_price': 85000, 'standard_price': 48000, 'taxes_id': tax_commands,
    'description_sale': 'Arabika Gayo medium roast dalam kemasan siap jual.',
    'attribute_line_ids': [Command.create({'attribute_id': pack_attribute.id, 'value_ids': [Command.set(pack_values.ids)]})],
}, context={'managed_ui': True})
set_value_extras(coffee, {'250 g': 0, '500 g': 65000, '1 kg': 175000})
set_variant_identity(coffee, {'250 g': ('KOPI-250', '8990000000110'), '500 g': ('KOPI-500', '8990000000127'), '1 kg': ('KOPI-1000', '8990000000134')})

service = ensure('product_service', 'product.template', {
    'name': 'Implementasi ERP Starter', 'default_code': 'SRV-ERP-START',
    'managed_product_kind': 'service', 'managed_track_inventory': False, 'sale_ok': True, 'purchase_ok': False,
    'categ_id': category_service.id, 'uom_id': unit.id, 'uom_po_id': unit.id,
    'list_price': 7500000, 'standard_price': 3500000, 'taxes_id': tax_commands,
    'description_sale': 'Paket onboarding, konfigurasi awal, dan pelatihan pengguna.',
}, context={'managed_ui': True})

ensure('supplier_shirt', 'product.supplierinfo', {
    'partner_id': vendor_textile.id, 'product_tmpl_id': shirt.id, 'min_qty': 20, 'price': 60000,
    'currency_id': currency.id, 'delay': 7, 'product_code': 'TM-KNS',
})
ensure('supplier_coffee', 'product.supplierinfo', {
    'partner_id': vendor_coffee.id, 'product_tmpl_id': coffee.id, 'min_qty': 10, 'price': 45000,
    'currency_id': currency.id, 'delay': 5, 'product_code': 'GAYO-ARABICA',
})

retail = ensure('pricelist_retail', 'product.pricelist', {
    'name': 'Retail Demo IDR', 'currency_id': currency.id, 'company_id': company.id, 'discount_policy': 'with_discount',
}, context={'managed_ui': True})
wholesale = ensure('pricelist_wholesale', 'product.pricelist', {
    'name': 'Grosir Demo IDR', 'currency_id': currency.id, 'company_id': company.id, 'discount_policy': 'with_discount',
}, context={'managed_ui': True})
shirt_m = shirt.product_variant_ids.filtered(lambda item: item.managed_variant_name == 'M')
shirt_l = shirt.product_variant_ids.filtered(lambda item: item.managed_variant_name == 'L')
coffee_250 = coffee.product_variant_ids.filtered(lambda item: item.managed_variant_name == '250 g')
coffee_500 = coffee.product_variant_ids.filtered(lambda item: item.managed_variant_name == '500 g')
for key, pricelist, product, price, qty in [
    ('retail_shirt_m', retail, shirt_m, 130000, 1), ('retail_shirt_l', retail, shirt_l, 145000, 1),
    ('retail_coffee_250', retail, coffee_250, 85000, 1), ('retail_coffee_500', retail, coffee_500, 145000, 1),
    ('wholesale_shirt', wholesale, shirt.product_variant_ids[:1], 105000, 12),
    ('wholesale_coffee', wholesale, coffee_250, 72000, 24),
]:
    ensure(f'price_{key}', 'product.pricelist.item', {
        'pricelist_id': pricelist.id, 'applied_on': '0_product_variant',
        'product_tmpl_id': product.product_tmpl_id.id, 'product_id': product.id,
        'compute_price': 'fixed', 'fixed_price': price, 'min_quantity': qty,
    })

for customer, pricelist in [(customer_nusantara, retail), (customer_cakrawala, wholesale), (customer_rasa, retail)]:
    values = {'property_product_pricelist': pricelist.id}
    if payment_term:
        values['property_payment_term_id'] = payment_term.id
    customer.with_company(company).write(values)

if warehouse:
    for product, target in [(variant, 40.0) for variant in shirt.product_variant_ids] + [(variant, 60.0) for variant in coffee.product_variant_ids]:
        current = env['stock.quant']._get_available_quantity(product, warehouse.lot_stock_id)
        if current != target:
            env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, target - current)

# Sales: draft, sent, confirmed, delivery, and invoice examples.
order_base = {
    'company_id': company.id, 'warehouse_id': warehouse.id, 'user_id': env.ref('base.user_admin').id,
}
quote_draft = ensure_order('quote_draft', {
    **order_base, 'partner_id': customer_nusantara.id, 'pricelist_id': retail.id,
    'client_order_ref': 'PO-DEMO-1001', 'validity_date': fields.Date.today() + timedelta(days=14),
    'order_line': [
        Command.create({'product_id': shirt_m.id, 'product_uom_qty': 2}),
        Command.create({'product_id': service.product_variant_id.id, 'product_uom_qty': 1}),
    ],
}, 'draft')
quote_sent = ensure_order('quote_sent', {
    **order_base, 'partner_id': customer_cakrawala.id, 'pricelist_id': wholesale.id,
    'client_order_ref': 'RFQ-DEMO-2202', 'validity_date': fields.Date.today() + timedelta(days=7),
    'order_line': [Command.create({'product_id': coffee_250.id, 'product_uom_qty': 24})],
}, 'sent')
order_pending = ensure_order('order_pending', {
    **order_base, 'partner_id': customer_rasa.id, 'pricelist_id': retail.id,
    'client_order_ref': 'PO-DEMO-3303',
    'order_line': [Command.create({'product_id': coffee_500.id, 'product_uom_qty': 8})],
}, 'sale')
order_invoice = ensure_order('order_invoice', {
    **order_base, 'partner_id': customer_nusantara.id, 'pricelist_id': retail.id,
    'client_order_ref': 'PO-DEMO-4404',
    'order_line': [Command.create({'product_id': service.product_variant_id.id, 'product_uom_qty': 1})],
}, 'sale')
if not order_invoice.invoice_ids and order_invoice.invoice_status == 'to invoice':
    invoice = order_invoice._create_invoices()
    remember('invoice_service', invoice)

# Numbering showcase: PO, GR, DO, INV, CN, RCPT, and PAY use KODEYYMMNNNNNN.
purchase_order = ensure_purchase_order('purchase_textile', {
    'partner_id': vendor_textile.id,
    'company_id': company.id,
    'picking_type_id': warehouse.in_type_id.id,
    'date_order': fields.Datetime.now(),
    'order_line': [Command.create({
        'product_id': shirt.product_variant_ids[:1].id,
        'name': 'Kaos Nusantara untuk restock demo',
        'product_qty': 20,
        'product_uom': unit.id,
        'price_unit': 60000,
        'date_planned': fields.Datetime.now() + timedelta(days=7),
    })],
}, confirm=True)
receipt = existing('receipt_textile') or purchase_order.picking_ids[:1]
if receipt and receipt.state != 'done':
    receipt = validate_picking(receipt)
    remember('receipt_textile', receipt)

order_paid = ensure_order('order_paid', {
    **order_base, 'partner_id': customer_cakrawala.id, 'pricelist_id': wholesale.id,
    'client_order_ref': 'PO-DEMO-5505',
    'order_line': [Command.create({'product_id': shirt_l.id, 'product_uom_qty': 12})],
}, 'sale')
delivery = existing('delivery_paid') or order_paid.picking_ids[:1]
if delivery and delivery.state != 'done':
    delivery = validate_picking(delivery)
    remember('delivery_paid', delivery)
if bank_journal and order_paid.invoice_status == 'to invoice':
    ensure_paid_invoice('invoice_paid', order_paid, bank_journal)

credit_note = existing('credit_note_demo')
if not credit_note:
    credit_note = env['account.move'].create({
        'move_type': 'out_refund',
        'partner_id': customer_nusantara.id,
        'invoice_date': fields.Date.today(),
        'ref': 'Koreksi harga demo',
        'invoice_line_ids': [Command.create({
            'product_id': service.product_variant_id.id,
            'name': 'Koreksi biaya implementasi',
            'quantity': 1,
            'price_unit': 250000,
        })],
    })
    credit_note.action_post()
    remember('credit_note_demo', credit_note)

vendor_payment = existing('vendor_payment_demo')
if not vendor_payment and bank_journal:
    payment_method = bank_journal.outbound_payment_method_line_ids[:1]
    vendor_payment = env['account.payment'].create({
        'payment_type': 'outbound',
        'partner_type': 'supplier',
        'partner_id': vendor_textile.id,
        'amount': 1200000,
        'date': fields.Date.today(),
        'journal_id': bank_journal.id,
        'payment_method_line_id': payment_method.id,
        'payment_reference': purchase_order.name,
    })
    vendor_payment.action_post()
    remember('vendor_payment_demo', vendor_payment)

activity_type = env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
if activity_type and not quote_draft.activity_ids:
    quote_draft.activity_schedule('mail.mail_activity_data_todo', date_deadline=fields.Date.today() + timedelta(days=2), summary='Follow-up penawaran demo')

# Inbox showcase.
channel = ensure('channel_sales', 'mail.channel', {
    'name': 'Tim Sales Demo', 'channel_type': 'channel', 'description': 'Koordinasi penawaran dan pesanan demo.',
})
admin_partner = env.ref('base.user_admin').partner_id
if admin_partner not in channel.channel_partner_ids:
    channel.write({'channel_partner_ids': [Command.link(admin_partner.id)]})
if not channel.message_ids.filtered(lambda message: message.body and 'Selamat datang di channel demo Sales' in str(message.body)):
    channel.message_post(body='Selamat datang di channel demo Sales. Gunakan data ini untuk mencoba Penawaran dan Pesanan.', message_type='comment', subtype_xmlid='mail.mt_comment')

# Settings showcase role; no password or login credential is created.
role = ensure('role_sales_demo', 'managed.settings.role', {'name': 'Sales Demo'})
permission_keys = {'contacts.customers', 'products.products', 'products.pricelists', 'sales.quotations', 'sales.orders'}
for key in permission_keys:
    if key in env['managed.settings.registry']._managed_registry()['permissions'] and not role.grant_ids.filtered(lambda grant: grant.permission_key == key):
        env['managed.settings.role.grant'].with_context(managed_settings_bootstrap=True).create({
            'role_id': role.id, 'permission_key': key, 'level': 'write' if key.startswith('sales.') else 'read',
        })

env.flush_all()
assert existing('customer_nusantara') and existing('product_shirt') and existing('quote_draft')
assert quote_draft.order_line and quote_sent.state == 'sent' and order_pending.state == 'sale'
numbered = {
    'penawaran': quote_draft.name,
    'pembelian': purchase_order.name,
    'penerimaan': receipt.name if receipt else None,
    'pengiriman': delivery.name if delivery else None,
    'faktur': order_paid.invoice_ids[:1].name,
    'nota_kredit': credit_note.name,
    'pembayaran_masuk': existing('invoice_paid_payment').name if existing('invoice_paid_payment') else None,
    'pembayaran_keluar': vendor_payment.name if vendor_payment else None,
}
expected_prefixes = {
    'penawaran': 'SO', 'pembelian': 'PO', 'penerimaan': 'GR', 'pengiriman': 'DO',
    'faktur': 'INV', 'nota_kredit': 'CN', 'pembayaran_masuk': 'RCPT', 'pembayaran_keluar': 'PAY',
}
for key, prefix in expected_prefixes.items():
    assert numbered[key] and numbered[key].startswith(prefix), (key, numbered[key])
env.cr.commit()
print('managed demo seed complete')
print({
    'customers': env['managed.partner.role'].search_count([('role', '=', 'customer'), ('company_id', '=', company.id)]),
    'vendors': env['managed.partner.role'].search_count([('role', '=', 'vendor'), ('company_id', '=', company.id)]),
    'products': env['product.template'].search_count([('categ_id', 'child_of', category_demo.id)]),
    'variants': env['product.product'].search_count([('product_tmpl_id.categ_id', 'child_of', category_demo.id)]),
    'quotations': env['sale.order'].search_count([('state', 'in', ('draft', 'sent'))]),
    'orders': env['sale.order'].search_count([('state', 'in', ('sale', 'done'))]),
    'document_numbers': numbered,
})
