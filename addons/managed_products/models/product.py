# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    managed_sku_normalized = fields.Char(compute='_compute_managed_sku', store=True, index=True)
    managed_variant_name = fields.Char(compute='_compute_managed_variant_name', string='Variant')

    @api.depends('product_template_attribute_value_ids.name')
    def _compute_managed_variant_name(self):
        for product in self:
            product.managed_variant_name = product.product_template_attribute_value_ids._get_combination_name() or _('Default')

    @api.depends('default_code')
    def _compute_managed_sku(self):
        for product in self:
            product.managed_sku_normalized = (product.default_code or '').strip().upper() or False

    def _check_managed_sku(self):
        if not self.env.context.get('managed_ui'):
            return
        Product = self.with_context(active_test=False, managed_ui=False).sudo()
        for product in self.filtered('managed_sku_normalized'):
            company_id = product.product_tmpl_id.company_id.id
            duplicate = Product.search([
                ('managed_sku_normalized', '=', product.managed_sku_normalized),
                ('id', '!=', product.id),
                ('product_tmpl_id.company_id', 'in', [False, company_id] if company_id else [False]),
            ], limit=1)
            if duplicate:
                raise ValidationError(_('SKU %(sku)s already belongs to %(product)s.', sku=product.default_code, product=duplicate.display_name))

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products._check_managed_sku()
        return products

    def write(self, vals):
        result = super().write(vals)
        self._check_managed_sku()
        return result


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui'):
            for vals in vals_list:
                vals['name'] = (vals.get('name') or '').strip()
                if not vals['name']:
                    raise ValidationError(_('Nama atribut wajib diisi.'))
        attributes = super().create(vals_list)
        attributes._check_managed_duplicate_names()
        return attributes

    def write(self, vals):
        if self.env.context.get('managed_ui') and 'name' in vals:
            vals['name'] = (vals.get('name') or '').strip()
            if not vals['name']:
                raise ValidationError(_('Nama atribut wajib diisi.'))
        result = super().write(vals)
        self._check_managed_duplicate_names()
        return result

    def _check_managed_duplicate_names(self):
        if not self.env.context.get('managed_ui'):
            return
        Attribute = self.with_context(active_test=False, managed_ui=False).sudo()
        for attribute in self:
            duplicate = Attribute.search([
                ('id', '!=', attribute.id),
                ('name', '=ilike', attribute.name.strip()),
            ], limit=1)
            if duplicate:
                raise ValidationError(_('Atribut %(name)s sudah ada.', name=attribute.name))

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'managed_products.action_product_attributes':
            return super()._managed_ui_contract(action_xmlid)
        value_fields = self.env['product.attribute.value']._fields
        value_columns = [name for name in ('name', 'html_color', 'is_custom', 'sequence') if name in value_fields]
        display_selection = [('radio', 'Daftar pilihan'), ('pills', 'Tombol pilihan'), ('select', 'Dropdown'), ('color', 'Pilihan warna')]
        creation_selection = [('always', 'Saat produk disimpan'), ('dynamic', 'Saat digunakan dalam transaksi'), ('no_variant', 'Tidak membuat varian')]
        return {
            'list': {
                'title': 'Atribut produk',
                'fields': [
                    {'name': 'name', 'label': 'Nama atribut'},
                    {'name': 'display_type', 'label': 'Tampilan', 'selection': display_selection},
                    {'name': 'create_variant', 'label': 'Pembuatan varian', 'selection': creation_selection},
                    {'name': 'number_related_products', 'label': 'Digunakan oleh produk'},
                ],
                'default_order': 'sequence, name',
            },
            'form': {
                'title': 'Atribut produk',
                'fields': [
                    {'name': 'name', 'label': 'Nama atribut', 'placeholder': 'Contoh: Warna, Ukuran, Isi kemasan'},
                    {'name': 'display_type', 'label': 'Cara pilihan ditampilkan', 'selection': display_selection},
                    {'name': 'create_variant', 'label': 'Cara varian dibuat', 'selection': creation_selection},
                    {'name': 'value_ids', 'label': 'Pilihan nilai', 'widget': 'managed_attribute_values', 'relation': {
                        'editable': True,
                        'inverse_field': 'attribute_id',
                        'columns': [
                            {'name': name, **({'label': 'Nama nilai', 'placeholder': 'Contoh: 250 ml, Merah, XL'} if name == 'name' else {'label': 'Warna'} if name == 'html_color' else {'label': 'Izinkan nilai bebas'} if name == 'is_custom' else {'label': 'Urutan'})}
                            for name in value_columns
                        ],
                    }},
                    {'name': 'number_related_products', 'label': 'Digunakan oleh produk'},
                ],
                'write_fields': ['name', 'display_type', 'create_variant', 'value_ids'],
                'buttons': [],
            },
        }


class ProductAttributeValue(models.Model):
    _inherit = 'product.attribute.value'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui'):
            for vals in vals_list:
                vals['name'] = (vals.get('name') or '').strip()
                if not vals['name']:
                    raise ValidationError(_('Nama nilai atribut wajib diisi.'))
        values = super().create(vals_list)
        values._check_managed_duplicate_names()
        return values

    def write(self, vals):
        if self.env.context.get('managed_ui') and 'name' in vals:
            vals['name'] = (vals.get('name') or '').strip()
            if not vals['name']:
                raise ValidationError(_('Nama nilai atribut wajib diisi.'))
        result = super().write(vals)
        self._check_managed_duplicate_names()
        return result

    def _check_managed_duplicate_names(self):
        if not self.env.context.get('managed_ui'):
            return
        Value = self.with_context(active_test=False, managed_ui=False).sudo()
        for value in self:
            duplicate = Value.search([
                ('id', '!=', value.id),
                ('attribute_id', '=', value.attribute_id.id),
                ('name', '=ilike', value.name.strip()),
            ], limit=1)
            if duplicate:
                raise ValidationError(_('Nilai %(name)s sudah ada pada atribut %(attribute)s.', name=value.name, attribute=value.attribute_id.name))


class ProductCategory(models.Model):
    _inherit = 'product.category'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui'):
            for vals in vals_list:
                vals['name'] = (vals.get('name') or '').strip()
                if not vals['name']:
                    raise ValidationError(_('Nama kategori wajib diisi.'))
        categories = super().create(vals_list)
        categories._check_managed_duplicate_names()
        return categories

    def write(self, vals):
        if self.env.context.get('managed_ui') and 'name' in vals:
            vals['name'] = (vals.get('name') or '').strip()
            if not vals['name']:
                raise ValidationError(_('Nama kategori wajib diisi.'))
        result = super().write(vals)
        self._check_managed_duplicate_names()
        return result

    def _check_managed_duplicate_names(self):
        if not self.env.context.get('managed_ui'):
            return
        Category = self.with_context(managed_ui=False).sudo()
        for category in self:
            if Category.search_count([
                ('id', '!=', category.id),
                ('parent_id', '=', category.parent_id.id or False),
                ('name', '=ilike', category.name),
            ]):
                raise ValidationError(_('Kategori %(name)s sudah ada pada induk yang sama.', name=category.name))

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'managed_products.action_product_categories':
            return super()._managed_ui_contract(action_xmlid)
        account_fields = []
        if self.env.user.has_group('account.group_account_user'):
            account_fields = [
                {'name': 'property_account_income_categ_id', 'label': 'Akun pendapatan'},
                {'name': 'property_account_expense_categ_id', 'label': 'Akun beban'},
            ]
        return {
            'list': {
                'title': 'Kategori produk',
                'fields': [
                    {'name': 'complete_name', 'label': 'Kategori'},
                    {'name': 'parent_id', 'label': 'Kategori induk'},
                    {'name': 'product_count', 'label': 'Jumlah produk'},
                ],
                'default_order': 'complete_name',
                'delete': False,
            },
            'form': {
                'title': 'Kategori produk',
                'fields': [
                    {'name': 'name', 'label': 'Nama kategori', 'placeholder': 'Contoh: Minuman, Elektronik, Jasa'},
                    {'name': 'parent_id', 'label': 'Kategori induk', 'help': 'Kosongkan untuk membuat kategori utama.'},
                    {'name': 'complete_name', 'label': 'Struktur kategori'},
                    {'name': 'product_count', 'label': 'Jumlah produk'},
                    *account_fields,
                ],
                'write_fields': ['name', 'parent_id', *[field['name'] for field in account_fields]],
                'buttons': [],
            },
        }


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui'):
            for vals in vals_list:
                vals['name'] = (vals.get('name') or '').strip()
                if not vals['name']:
                    raise ValidationError(_('Nama daftar harga wajib diisi.'))
        pricelists = super().create(vals_list)
        pricelists._check_managed_duplicate_names()
        return pricelists

    def write(self, vals):
        if self.env.context.get('managed_ui') and 'name' in vals:
            vals['name'] = (vals.get('name') or '').strip()
            if not vals['name']:
                raise ValidationError(_('Nama daftar harga wajib diisi.'))
        result = super().write(vals)
        self._check_managed_duplicate_names()
        return result

    def _check_managed_duplicate_names(self):
        if not self.env.context.get('managed_ui'):
            return
        Pricelist = self.with_context(active_test=False, managed_ui=False).sudo()
        for pricelist in self:
            if Pricelist.search_count([
                ('id', '!=', pricelist.id),
                ('company_id', '=', pricelist.company_id.id or False),
                ('currency_id', '=', pricelist.currency_id.id),
                ('name', '=ilike', pricelist.name),
            ]):
                raise ValidationError(_('Daftar harga %(name)s sudah ada untuk perusahaan dan mata uang ini.', name=pricelist.name))

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'managed_products.action_product_pricelists':
            return super()._managed_ui_contract(action_xmlid)
        item_fields = self.env['product.pricelist.item']._fields
        columns = [name for name in (
            'applied_on', 'categ_id', 'product_tmpl_id', 'product_id',
            'compute_price', 'fixed_price', 'percent_price', 'base', 'base_pricelist_id',
            'price_discount', 'price_surcharge', 'price_round', 'price_min_margin', 'price_max_margin',
            'min_quantity', 'date_start', 'date_end', 'name', 'price',
        ) if name in item_fields]
        labels = {
            'applied_on': 'Berlaku untuk', 'categ_id': 'Kategori produk', 'product_tmpl_id': 'Produk',
            'product_id': 'Variant', 'compute_price': 'Cara menentukan harga', 'fixed_price': 'Harga tetap',
            'percent_price': 'Diskon (%)', 'base': 'Harga acuan', 'base_pricelist_id': 'Daftar harga acuan',
            'price_discount': 'Diskon formula (%)', 'price_surcharge': 'Tambahan tetap',
            'price_round': 'Pembulatan', 'price_min_margin': 'Margin minimum',
            'price_max_margin': 'Margin maksimum', 'min_quantity': 'Minimum kuantitas',
            'date_start': 'Mulai berlaku', 'date_end': 'Berakhir', 'name': 'Cakupan', 'price': 'Hasil aturan',
        }
        selections = {
            'applied_on': [('3_global', 'Semua produk'), ('2_product_category', 'Kategori produk'), ('1_product', 'Produk tertentu'), ('0_product_variant', 'Variant tertentu')],
            'compute_price': [('fixed', 'Harga tetap'), ('percentage', 'Diskon persentase'), ('formula', 'Formula lanjutan')],
            'base': [('list_price', 'Harga jual produk'), ('standard_price', 'Cost'), ('pricelist', 'Daftar harga lain')],
        }
        relation_columns = [
            {'name': name, 'label': labels[name], **({'selection': selections[name]} if name in selections else {})}
            for name in columns
        ]
        return {
            'list': {
                'title': 'Daftar harga',
                'fields': [
                    {'name': 'name', 'label': 'Nama daftar harga'},
                    {'name': 'currency_id', 'label': 'Mata uang'},
                    {'name': 'company_id', 'label': 'Perusahaan'},
                    {'name': 'active', 'label': 'Aktif'},
                ],
                'default_order': 'sequence asc, name asc',
                'filters': [{'name': 'archived', 'label': 'Diarsipkan', 'domain': [('active', '=', False)]}],
                'delete': False,
            },
            'form': {
                'title': 'Daftar harga',
                'fields': [
                    {'name': 'name', 'label': 'Nama daftar harga', 'placeholder': 'Contoh: Retail IDR, Grosir, Export USD'},
                    {'name': 'currency_id', 'label': 'Mata uang'},
                    {'name': 'company_id', 'label': 'Perusahaan', 'help': 'Kosongkan agar dapat digunakan semua perusahaan yang diizinkan.'},
                    {'name': 'active', 'label': 'Aktif'},
                    {'name': 'discount_policy', 'label': 'Tampilan diskon', 'selection': [
                        ('with_discount', 'Tampilkan harga akhir'),
                        ('without_discount', 'Tampilkan harga publik dan diskon'),
                    ]},
                    {'name': 'country_group_ids', 'label': 'Kelompok negara'},
                    {'name': 'item_ids', 'label': 'Aturan harga', 'widget': 'managed_pricelist_rules', 'relation': {
                        'editable': True,
                        'inverse_field': 'pricelist_id',
                        'columns': relation_columns,
                    }},
                ],
                'write_fields': ['name', 'currency_id', 'company_id', 'active', 'discount_policy', 'country_group_ids', 'item_ids'],
                'buttons': [],
            },
        }


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    managed_creation_mode = fields.Selection(related='attribute_id.create_variant', string='Creation Mode')
    managed_value_prices = fields.Json(compute='_compute_managed_value_prices', inverse='_inverse_managed_value_prices')

    @api.depends('product_template_value_ids.price_extra', 'product_template_value_ids.product_attribute_value_id')
    def _compute_managed_value_prices(self):
        for line in self:
            line.managed_value_prices = {
                str(value.product_attribute_value_id.id): value.price_extra
                for value in line.product_template_value_ids
            }

    def _inverse_managed_value_prices(self):
        for line in self:
            prices = line.managed_value_prices or {}
            for value in line.product_template_value_ids:
                key = str(value.product_attribute_value_id.id)
                if key in prices:
                    value.price_extra = prices[key] or 0.0


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    managed_product_kind = fields.Selection(
        [('goods', 'Goods'), ('service', 'Service')],
        compute='_compute_managed_product_controls', inverse='_inverse_managed_product_controls',
        store=True, readonly=False, precompute=True, string='Managed Product Kind',
    )
    managed_track_inventory = fields.Boolean(
        compute='_compute_managed_product_controls', inverse='_inverse_managed_product_controls',
        store=True, readonly=False, precompute=True, string='Track Inventory',
    )
    managed_variant_preview_count = fields.Integer(compute='_compute_managed_variant_preview_count', string='Variant Combinations')

    @api.depends('attribute_line_ids.active', 'attribute_line_ids.value_ids', 'attribute_line_ids.attribute_id.create_variant')
    def _compute_managed_variant_preview_count(self):
        for product in self:
            lines = product.attribute_line_ids.filtered(
                lambda line: line.active and line.attribute_id.create_variant != 'no_variant'
            )
            count = 1
            for line in lines:
                count *= len(line.value_ids)
            product.managed_variant_preview_count = count if lines else 1

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        detailed_type = defaults.get('detailed_type') or 'consu'
        if 'managed_product_kind' in fields_list:
            defaults['managed_product_kind'] = 'service' if detailed_type == 'service' else 'goods'
        if 'managed_track_inventory' in fields_list:
            defaults['managed_track_inventory'] = detailed_type == 'product'
        return defaults

    @api.depends('detailed_type')
    def _compute_managed_product_controls(self):
        for product in self:
            product.managed_product_kind = 'service' if product.detailed_type == 'service' else 'goods'
            product.managed_track_inventory = product.detailed_type == 'product'

    def _inverse_managed_product_controls(self):
        for product in self:
            product.detailed_type = 'service' if product.managed_product_kind == 'service' else 'product' if product.managed_track_inventory else 'consu'

    @api.onchange('managed_product_kind', 'managed_track_inventory')
    def _onchange_managed_product_controls(self):
        self._inverse_managed_product_controls()

    @api.model
    def _managed_attribute_prices(self, commands):
        prices = []
        for command in commands or []:
            if not isinstance(command, (list, tuple)) or len(command) < 3 or not isinstance(command[2], dict):
                continue
            data = command[2]
            if 'managed_value_prices' in data:
                prices.append((command[1] if command[0] == 1 else False, data.get('attribute_id'), data['managed_value_prices'] or {}))
        return prices

    def _apply_managed_attribute_prices(self, prices):
        for product in self:
            for line_id, attribute_id, values in prices:
                line = product.attribute_line_ids.filtered(
                    lambda item: item.id == line_id if line_id else item.attribute_id.id == attribute_id
                )[:1]
                for value in line.product_template_value_ids:
                    key = str(value.product_attribute_value_id.id)
                    if key in values:
                        value.price_extra = values[key] or 0.0

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui') and not self.env.company.managed_product_variants:
            for vals in vals_list:
                if vals.get('attribute_line_ids'):
                    raise ValidationError(_('Enable Product Variants before adding attributes.'))
        prices = [self._managed_attribute_prices(vals.get('attribute_line_ids')) for vals in vals_list]
        products = super().create(vals_list)
        for product, product_prices in zip(products, prices):
            product._apply_managed_attribute_prices(product_prices)
        return products

    def write(self, vals):
        if self.env.context.get('managed_ui') and vals.get('attribute_line_ids') and not self.env.company.managed_product_variants:
            raise ValidationError(_('Enable Product Variants before adding attributes.'))
        prices = self._managed_attribute_prices(vals.get('attribute_line_ids'))
        result = super().write(vals)
        self._apply_managed_attribute_prices(prices)
        return result

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        supported = {
            'managed_products.action_products',
            'product.product_template_action', 'product.product_template_action_all',
            'account.product_product_action_sellable', 'account.product_product_action_purchasable',
            'sale.product_template_action', 'purchase.product_normal_action_puchased',
            'stock.product_template_action_product', 'mrp.product_template_action',
        }
        if action_xmlid not in supported:
            return super()._managed_ui_contract(action_xmlid)

        fields_by_name = self._fields
        supplier_fields = self.env['product.supplierinfo']._fields
        attribute_line_fields = self.env['product.template.attribute.line']._fields
        variant_fields = self.env['product.product']._fields
        def available(*names):
            return [name for name in names if name in fields_by_name]
        def available_supplier_fields(*names):
            return [name for name in names if name in supplier_fields]
        def available_attribute_line_fields(*names):
            return [name for name in names if name in attribute_line_fields]
        def available_variant_fields(*names):
            return [name for name in names if name in variant_fields]

        list_fields = available(
            'image_128', 'default_code', 'name', 'managed_product_kind',
            'categ_id', 'list_price', 'standard_price', 'uom_id',
            'qty_available', 'active',
        )
        form_fields = available(
            'image_1920', 'name', 'default_code', 'barcode',
            'managed_product_kind', 'managed_track_inventory', 'detailed_type',
            'sale_ok', 'purchase_ok', 'active',
            'categ_id', 'uom_id', 'uom_po_id',
            'list_price', 'standard_price', 'taxes_id', 'supplier_taxes_id',
            'invoice_policy', 'sale_delay', 'purchase_method', 'seller_ids',
            'l10n_id_product_code', 'tracking', 'responsible_id', 'route_ids',
            *(('property_account_income_id', 'property_account_expense_id') if self.env.user.has_group('account.group_account_user') else ()),
            'weight', 'volume', 'description_sale', 'description_purchase', 'description',
            'attribute_line_ids', 'product_variant_ids', 'product_variant_count', 'managed_variant_preview_count',
            'company_id', 'currency_id', 'qty_available', 'virtual_available',
        )
        readonly = {'currency_id', 'qty_available', 'virtual_available', 'detailed_type', 'product_variant_count', 'managed_variant_preview_count'}
        write_fields = [name for name in form_fields if name not in readonly]
        filters = [
            {'name': 'sellable', 'label': 'Can be Sold', 'domain': [('sale_ok', '=', True)]},
            {'name': 'purchasable', 'label': 'Can be Purchased', 'domain': [('purchase_ok', '=', True)]},
            {'name': 'goods', 'label': 'Goods', 'domain': [('detailed_type', 'in', ['consu', 'product'])]},
            {'name': 'services', 'label': 'Services', 'domain': [('detailed_type', '=', 'service')]},
        ]
        return {
            'list': {
                'title': 'Products',
                'fields': [
                    {'name': name, **({'widget': 'image'} if name == 'image_128' else {})}
                    for name in list_fields
                ],
                'read_fields': available('currency_id'),
                'default_order': 'priority desc, name asc',
                'filters': filters,
            },
            'form': {
                'title': 'Product',
                'fields': [
                    ({'name': name, 'widget': 'image'} if name == 'image_1920' else
                     {'name': name, 'label': 'SKU'} if name == 'default_code' else
                     {'name': name, 'label': 'Product Type'} if name in ('managed_product_kind', 'detailed_type') else
                     {'name': name, 'widget': 'managed_supplier_prices', 'relation': {
                         'editable': True,
                         'inverse_field': 'product_tmpl_id',
                         'columns': available_supplier_fields(
                             'partner_id', 'product_id', 'product_code', 'product_name', 'min_qty', 'price',
                             'currency_id', 'delay', 'date_start', 'date_end',
                         ),
                     }} if name == 'seller_ids' else
                     {'name': name, 'widget': 'managed_attribute_lines', 'relation': {
                         'editable': True,
                         'inverse_field': 'product_tmpl_id',
                         'columns': available_attribute_line_fields(
                             'attribute_id', 'value_ids', 'managed_creation_mode', 'managed_value_prices', 'active',
                         ),
                     }} if name == 'attribute_line_ids' else
                     {'name': name, 'widget': 'managed_variants', 'relation': {
                         'editable': True,
                         'inverse_field': 'product_tmpl_id',
                         'columns': [
                             {'name': column, **({'widget': 'image'} if column == 'image_variant_1920' else {})}
                             for column in available_variant_fields(
                                 'managed_variant_name', 'image_variant_1920', 'default_code', 'barcode',
                                 'lst_price', 'standard_price', 'weight', 'volume', 'qty_available',
                                 'virtual_available', 'active',
                             )
                         ],
                     }} if name == 'product_variant_ids' else
                     {'name': name})
                    for name in form_fields
                ],
                'write_fields': write_fields,
                'buttons': [],
            },
        }
