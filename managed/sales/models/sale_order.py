# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    managed_discount_mode = fields.Selection(
        [('percentage', 'Persentase'), ('fixed', 'Nominal tetap')],
        default='percentage', required=True, string='Jenis diskon',
    )
    managed_discount_fixed = fields.Monetary(
        currency_field='currency_id', default=0, string='Diskon tetap',
    )

    @api.onchange('managed_discount_mode', 'managed_discount_fixed', 'product_uom_qty', 'price_unit')
    def _onchange_managed_fixed_discount(self):
        for line in self:
            if line.managed_discount_mode == 'fixed':
                base = line.product_uom_qty * line.price_unit
                line.discount = line.managed_discount_fixed / base * 100 if base else 0
            else:
                line.managed_discount_fixed = 0

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui'):
            vals_list = [self._managed_prepare_discount_values(values) for values in vals_list]
        return super().create(vals_list)

    def write(self, values):
        relevant = {'managed_discount_mode', 'managed_discount_fixed', 'product_uom_qty', 'price_unit'}
        if self.env.context.get('managed_ui') and relevant.intersection(values):
            for line in self:
                super(SaleOrderLine, line).write(line._managed_prepare_discount_values(values))
            return True
        return super().write(values)

    def _managed_prepare_discount_values(self, values):
        values = dict(values)
        record = self if len(self) == 1 else self.browse()
        mode = values.get('managed_discount_mode', record.managed_discount_mode or 'percentage')
        if mode == 'fixed':
            quantity = values.get('product_uom_qty', record.product_uom_qty or 0)
            price = values.get('price_unit', record.price_unit or 0)
            fixed = values.get('managed_discount_fixed', record.managed_discount_fixed or 0)
            base = quantity * price
            values['discount'] = fixed / base * 100 if base else 0
        else:
            values['managed_discount_fixed'] = 0
        return values

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _managed_configure_document_sequence(self):
        sequence = self.env.ref('sale.seq_sale_order').sudo()
        sequence.write({
            'name': 'Sales Order',
            'prefix': 'SO%(y)s%(month)s',
            'padding': 6,
            'use_date_range': True,
            'managed_monthly_reset': True,
        })
        return sequence

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid not in {'sales.action_quotations', 'sales.action_orders'}:
            return super()._managed_ui_contract(action_xmlid)

        quotations = action_xmlid == 'sales.action_quotations'
        locked = {'readonly': [('state', 'in', ['done', 'cancel'])]}
        confirmed = {'readonly': [('state', 'in', ['sale', 'done', 'cancel'])]}
        fields = [
            {'name': 'name', 'label': 'Nomor', 'modifiers': confirmed},
            {'name': 'partner_id', 'label': 'Pelanggan', 'widget': 'managed_customer_many2one', 'modifiers': confirmed},
            {'name': 'partner_invoice_id', 'label': 'Alamat tagih', 'widget': 'managed_order_address_many2one', 'modifiers': locked},
            {'name': 'partner_shipping_id', 'label': 'Alamat kirim', 'widget': 'managed_order_address_many2one', 'modifiers': locked},
            {'name': 'client_order_ref', 'label': 'Referensi pelanggan', 'modifiers': confirmed},
            {'name': 'date_order', 'label': 'Tanggal', 'modifiers': confirmed},
            {
                'name': 'validity_date', 'label': 'Berlaku sampai',
                'modifiers': {'readonly': confirmed['readonly'], 'invisible': [('state', 'in', ['sale', 'done'])]},
            },
            {'name': 'commitment_date', 'label': 'Tanggal kirim janji', 'modifiers': locked},
            {'name': 'user_id', 'label': 'Salesperson', 'widget': 'many2one_avatar_user', 'modifiers': confirmed},
            {'name': 'team_id', 'label': 'Tim penjualan', 'modifiers': confirmed},
            {'name': 'pricelist_id', 'label': 'Daftar harga', 'widget': 'managed_order_pricelist_many2one', 'modifiers': confirmed},
            {'name': 'payment_term_id', 'label': 'Termin pembayaran', 'widget': 'managed_order_payment_term_many2one', 'modifiers': locked},
            {'name': 'fiscal_position_id', 'label': 'Posisi fiskal', 'widget': 'managed_order_fiscal_position_many2one', 'modifiers': locked},
            {'name': 'warehouse_id', 'label': 'Gudang', 'widget': 'managed_order_warehouse_many2one', 'modifiers': confirmed},
            {'name': 'picking_policy', 'label': 'Kebijakan pengiriman', 'modifiers': confirmed, 'selection': [
                ('direct', 'Kirim saat siap'), ('one', 'Kirim sekaligus'),
            ]},
            {'name': 'incoterm', 'label': 'Incoterm', 'modifiers': confirmed},
            {'name': 'incoterm_location', 'label': 'Lokasi Incoterm', 'modifiers': confirmed},
            {
                'name': 'order_line', 'label': 'Produk dan layanan', 'widget': 'managed_sale_order_lines', 'modifiers': locked,
                'relation': {
                    'editable': True,
                    'inverse_field': 'order_id',
                    'columns': [
                        {'name': 'product_id', 'label': 'Produk / Variant', 'widget': 'managed_sale_product_many2one'},
                        {'name': 'name', 'label': 'Deskripsi'},
                        {'name': 'product_uom_qty', 'label': 'Kuantitas'},
                        {'name': 'product_uom', 'label': 'Satuan', 'widget': 'managed_sale_uom_many2one'},
                        {'name': 'price_unit', 'label': 'Harga satuan'},
                        {'name': 'managed_discount_mode', 'label': 'Jenis diskon'},
                        {'name': 'discount', 'label': 'Diskon', 'widget': 'percentage'},
                        {'name': 'managed_discount_fixed', 'label': 'Diskon tetap'},
                        {'name': 'tax_id', 'label': 'Pajak', 'widget': 'many2many_tags'},
                        {'name': 'price_subtotal', 'label': 'Subtotal'},
                        {'name': 'price_total', 'label': 'Total setelah pajak'},
                        {'name': 'currency_id', 'label': 'Mata uang'},
                        {'name': 'display_type', 'label': 'Tipe baris'},
                    ],
                },
            },
            {'name': 'note', 'label': 'Catatan dan syarat', 'modifiers': locked},
            {'name': 'amount_untaxed', 'label': 'Subtotal'},
            {'name': 'amount_tax', 'label': 'Pajak'},
            {'name': 'amount_total', 'label': 'Total'},
            {'name': 'currency_id', 'label': 'Mata uang'},
            {'name': 'picking_ids', 'label': 'Pengiriman'},
            {'name': 'invoice_ids', 'label': 'Faktur pelanggan'},
            {'name': 'delivery_count', 'label': 'Jumlah pengiriman'},
            {'name': 'invoice_count', 'label': 'Jumlah faktur'},
            {'name': 'delivery_status', 'label': 'Status pengiriman', 'selection': [
                ('pending', 'Belum diproses'), ('started', 'Diproses'), ('partial', 'Sebagian dikirim'), ('full', 'Selesai dikirim'),
            ]},
            {'name': 'invoice_status', 'label': 'Status tagihan', 'selection': [
                ('upselling', 'Perlu penyesuaian'), ('invoiced', 'Sudah ditagih'), ('to invoice', 'Perlu ditagih'), ('no', 'Belum dapat ditagih'),
            ]},
            {'name': 'state', 'label': 'Status', 'widget': 'statusbar', 'selection': [
                ('draft', 'Draf'), ('sent', 'Terkirim'), ('sale', 'Dikonfirmasi'), ('done', 'Selesai'), ('cancel', 'Dibatalkan'),
            ]},
        ]
        writable = {
            'partner_id', 'partner_invoice_id', 'partner_shipping_id', 'client_order_ref',
            'date_order', 'validity_date', 'commitment_date', 'user_id', 'team_id',
            'pricelist_id', 'payment_term_id', 'fiscal_position_id', 'warehouse_id', 'picking_policy',
            'incoterm', 'incoterm_location', 'order_line', 'note',
        }
        return {
            'list': {
                'title': 'Penawaran' if quotations else 'Pesanan',
                'fields': [
                    {'name': 'name', 'label': 'Nomor'},
                    {'name': 'partner_id', 'label': 'Pelanggan'},
                    {'name': 'date_order', 'label': 'Tanggal'},
                    {'name': 'validity_date', 'label': 'Berlaku sampai'} if quotations else {'name': 'delivery_status', 'label': 'Pengiriman', 'widget': 'badge'},
                    {'name': 'amount_total', 'label': 'Total'},
                    {'name': 'invoice_status', 'label': 'Status tagihan', 'widget': 'badge'} if not quotations else {'name': 'user_id', 'label': 'Salesperson', 'widget': 'many2one_avatar_user'},
                    {'name': 'state', 'label': 'Status', 'widget': 'badge'},
                ],
                'read_fields': ['currency_id'],
                'default_order': 'date_order desc, id desc',
                'create': quotations,
                'delete': False,
                'filters': [
                    {'name': 'mine', 'label': 'Milik saya', 'domain': [('user_id', '=', self.env.uid)]},
                    *([{'name': 'draft', 'label': 'Draf', 'domain': [('state', '=', 'draft')]}, {'name': 'sent', 'label': 'Terkirim', 'domain': [('state', '=', 'sent')]}] if quotations else [
                        {'name': 'to_deliver', 'label': 'Perlu dikirim', 'domain': [('delivery_status', 'in', ('pending', 'started', 'partial'))]},
                        {'name': 'to_invoice', 'label': 'Perlu ditagih', 'domain': [('invoice_status', '=', 'to invoice')]},
                    ]),
                ],
            },
            'form': {
                'title': 'Penawaran' if quotations else 'Pesanan',
                'fields': fields,
                'write_fields': [field['name'] for field in fields if field['name'] in writable],
                'create': quotations,
                'write': quotations,
                'status_field': 'state',
                'status_visible': ['draft', 'sent', 'sale', 'done'],
                'buttons': [
                    {
                        'name': 'action_quotation_send', 'label': 'Kirim penawaran', 'type': 'object', 'primary': True,
                        'modifiers': {'invisible': [('state', 'not in', ['draft', 'sent'])]},
                    },
                    {
                        'name': 'action_confirm', 'label': 'Konfirmasi pesanan', 'type': 'object', 'primary': True,
                        'modifiers': {'invisible': [('state', 'not in', ['draft', 'sent'])]},
                    },
                    {
                        'name': 'action_create_managed_invoice', 'label': 'Buat faktur', 'type': 'object', 'primary': True,
                        'modifiers': {'invisible': ['|', ('state', 'not in', ['sale', 'done']), ('invoice_status', 'not in', ['to invoice', 'no'])]},
                    },
                    {
                        'name': 'action_cancel', 'label': 'Batalkan', 'type': 'object',
                        'modifiers': {'invisible': [('state', 'not in', ['draft', 'sent', 'sale'])]},
                    },
                    {
                        'name': 'action_draft', 'label': 'Aktifkan kembali', 'type': 'object',
                        'modifiers': {'invisible': [('state', '!=', 'cancel')]},
                    },
                ],
            },
        }

    def _managed_related_documents(self):
        self.ensure_one()
        return [
            {
                'key': 'deliveries', 'label': _('Pengiriman'),
                'action_xmlid': 'inventory.action_deliveries', 'records': self.picking_ids,
                'status_field': 'managed_operation_status',
            },
            {
                'key': 'invoices', 'label': _('Faktur pelanggan'),
                'action_xmlid': 'finance.action_customer_invoices', 'records': self.invoice_ids,
                'status_field': 'payment_state',
                'status_labels': {
                    'not_paid': _('Belum dibayar'), 'in_payment': _('Dalam pembayaran'),
                    'paid': _('Lunas'), 'partial': _('Dibayar sebagian'),
                    'reversed': _('Dibalik'), 'invoicing_legacy': _('Legacy'),
                },
            },
        ]

    def action_create_managed_invoice(self):
        self.ensure_one()
        if self.state not in ('sale', 'done'):
            raise ValidationError(_('Hanya pesanan terkonfirmasi yang dapat dibuatkan faktur.'))
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_view_sale_advance_payment_inv')
        action['context'] = {
            **self.env.context,
            'active_model': 'sale.order',
            'active_id': self.id,
            'active_ids': self.ids,
            'default_sale_order_ids': [(6, 0, self.ids)],
        }
        return action

    def _check_managed_sales_contract(self):
        if not self.env.context.get('managed_ui'):
            return
        for order in self:
            if not order.partner_id:
                continue
            customer = order.partner_id.commercial_partner_id
            has_customer_role = self.env['managed.partner.role'].search_count([
                ('partner_id', '=', customer.id), ('company_id', '=', order.company_id.id), ('role', '=', 'customer'), ('active', '=', True),
            ])
            if not has_customer_role:
                raise ValidationError(_('Pelanggan harus dipilih dari Customer aktif.'))
            if order.pricelist_id.company_id and order.pricelist_id.company_id != order.company_id:
                raise ValidationError(_('Daftar harga harus tersedia untuk perusahaan pesanan.'))
            if order.payment_term_id.company_id and order.payment_term_id.company_id != order.company_id:
                raise ValidationError(_('Termin pembayaran harus tersedia untuk perusahaan pesanan.'))
            if order.fiscal_position_id and order.fiscal_position_id.company_id != order.company_id:
                raise ValidationError(_('Posisi fiskal harus milik perusahaan pesanan.'))
            if order.warehouse_id.company_id != order.company_id:
                raise ValidationError(_('Gudang harus milik perusahaan pesanan.'))
            for address, label in ((order.partner_invoice_id, _('Alamat tagih')), (order.partner_shipping_id, _('Alamat kirim'))):
                if address and address != customer and address.parent_id.commercial_partner_id != customer:
                    raise ValidationError(_('%(label)s harus milik pelanggan terpilih.', label=label))
            for line in order.order_line.filtered(lambda item: not item.display_type):
                if not line.product_id.sale_ok:
                    raise ValidationError(_('Produk %(product)s tidak dapat dijual.', product=line.product_id.display_name))
                if line.product_uom.category_id != line.product_id.uom_id.category_id:
                    raise ValidationError(_('Satuan untuk %(product)s harus satu kelompok dengan satuan produk.', product=line.product_id.display_name))

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._check_managed_sales_contract()
        return orders

    def write(self, vals):
        result = super().write(vals)
        if self.env.context.get('managed_ui') and 'pricelist_id' in vals:
            self.filtered(lambda order: order.state in ('draft', 'sent'))._recompute_prices()
        self._check_managed_sales_contract()
        return result
