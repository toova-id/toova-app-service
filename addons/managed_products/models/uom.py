# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class UomCategory(models.Model):
    _inherit = 'uom.category'

    managed_unit_count = fields.Integer(compute='_compute_managed_unit_count', string='Jumlah satuan')

    @api.depends('uom_ids.active')
    def _compute_managed_unit_count(self):
        for category in self:
            category.managed_unit_count = len(category.uom_ids.filtered('active'))

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui'):
            for vals in vals_list:
                vals['name'] = (vals.get('name') or '').strip()
                if not vals['name']:
                    raise ValidationError(_('Nama kelompok satuan wajib diisi.'))
        categories = super().create(vals_list)
        categories._check_managed_duplicate_names()
        categories._check_managed_structure()
        return categories

    def write(self, vals):
        if self.env.context.get('managed_ui') and 'name' in vals:
            vals['name'] = (vals.get('name') or '').strip()
            if not vals['name']:
                raise ValidationError(_('Nama kelompok satuan wajib diisi.'))
        result = super().write(vals)
        self._check_managed_duplicate_names()
        self._check_managed_structure()
        return result

    def _check_managed_structure(self):
        if not self.env.context.get('managed_ui'):
            return
        for category in self:
            active_units = category.uom_ids.filtered('active')
            if len(active_units.filtered(lambda unit: unit.uom_type == 'reference')) != 1:
                raise ValidationError(_('Kelompok satuan harus memiliki tepat satu satuan dasar aktif.'))

    def _check_managed_duplicate_names(self):
        if not self.env.context.get('managed_ui'):
            return
        Category = self.with_context(managed_ui=False).sudo()
        for category in self:
            if Category.search_count([('id', '!=', category.id), ('name', '=ilike', category.name)]):
                raise ValidationError(_('Kelompok satuan %(name)s sudah ada.', name=category.name))

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'managed_products.action_uom_categories':
            return super()._managed_ui_contract(action_xmlid)
        unit_fields = self.env['uom.uom']._fields
        columns = [name for name in (
            'name', 'uom_type', 'managed_base_quantity', 'rounding', 'active', 'managed_usage_count', 'managed_conversion_locked',
        ) if name in unit_fields]
        labels = {
            'name': 'Nama satuan', 'uom_type': 'Jenis', 'managed_base_quantity': 'Nilai dalam satuan dasar',
            'rounding': 'Kuantitas minimum', 'active': 'Aktif', 'managed_usage_count': 'Pemakaian', 'managed_conversion_locked': 'Konversi terkunci',
        }
        return {
            'list': {
                'title': 'Satuan',
                'fields': [
                    {'name': 'name', 'label': 'Kelompok satuan'},
                    {'name': 'managed_unit_count', 'label': 'Jumlah satuan'},
                ],
                'default_order': 'name',
                'delete': False,
            },
            'form': {
                'title': 'Satuan',
                'fields': [
                    {'name': 'name', 'label': 'Nama kelompok satuan', 'placeholder': 'Contoh: Volume, Berat, Panjang'},
                    {'name': 'managed_unit_count', 'label': 'Jumlah satuan'},
                    {'name': 'uom_ids', 'label': 'Satuan & konversi', 'widget': 'managed_uom_units', 'relation': {
                        'editable': True,
                        'inverse_field': 'category_id',
                        'columns': [
                            {'name': name, 'label': labels[name], **({
                                'selection': [('reference', 'Satuan dasar'), ('smaller', 'Lebih kecil'), ('bigger', 'Lebih besar')],
                            } if name == 'uom_type' else {})}
                            for name in columns
                        ],
                    }},
                ],
                'write_fields': ['name', 'uom_ids'],
                'buttons': [],
            },
        }


class UomUom(models.Model):
    _inherit = 'uom.uom'

    managed_base_quantity = fields.Float(
        compute='_compute_managed_base_quantity', inverse='_inverse_managed_base_quantity',
        digits=(16, 12), string='Nilai dalam satuan dasar',
        help='Jumlah satuan dasar yang setara dengan satu unit ini.',
    )
    managed_usage_count = fields.Integer(compute='_compute_managed_usage', string='Pemakaian')
    managed_conversion_locked = fields.Boolean(compute='_compute_managed_usage', string='Konversi terkunci')

    @api.depends('factor')
    def _compute_managed_base_quantity(self):
        for unit in self:
            unit.managed_base_quantity = unit.factor and 1.0 / unit.factor or 0.0

    def _inverse_managed_base_quantity(self):
        for unit in self:
            if unit.managed_base_quantity <= 0:
                raise ValidationError(_('Nilai konversi harus lebih besar dari 0.'))
            quantity = unit.managed_base_quantity
            unit.factor = 1.0 / quantity
            unit.uom_type = 'reference' if float_compare(quantity, 1.0, precision_digits=12) == 0 else 'bigger' if quantity > 1 else 'smaller'

    def _compute_managed_usage(self):
        Product = self.env['product.template'].sudo().with_context(active_test=False)
        for unit in self:
            unit.managed_usage_count = Product.search_count(['|', ('uom_id', '=', unit.id), ('uom_po_id', '=', unit.id)])
            unit.managed_conversion_locked = unit._managed_transaction_usage()

    def _managed_transaction_usage(self):
        self.ensure_one()
        checks = (
            ('stock.move', 'product_uom'), ('stock.move.line', 'product_uom_id'),
            ('sale.order.line', 'product_uom'), ('purchase.order.line', 'product_uom'),
            ('account.move.line', 'product_uom_id'),
        )
        return any(model in self.env and self.env[model].sudo().search_count([(field, '=', self.id)], limit=1) for model, field in checks)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui'):
            for vals in vals_list:
                vals['name'] = (vals.get('name') or '').strip()
                if not vals['name']:
                    raise ValidationError(_('Nama satuan wajib diisi.'))
                quantity = vals.pop('managed_base_quantity', 1.0)
                if quantity <= 0:
                    raise ValidationError(_('Nilai konversi harus lebih besar dari 0.'))
                vals['factor'] = 1.0 / quantity
                vals['uom_type'] = 'reference' if float_compare(quantity, 1.0, precision_digits=12) == 0 else 'bigger' if quantity > 1 else 'smaller'
        units = super().create(vals_list)
        units._check_managed_duplicate_names()
        return units

    def write(self, vals):
        values = dict(vals)
        if self.env.context.get('managed_ui'):
            if 'name' in values:
                values['name'] = (values.get('name') or '').strip()
                if not values['name']:
                    raise ValidationError(_('Nama satuan wajib diisi.'))
            if values.get('active') is False and any(unit.uom_type == 'reference' for unit in self):
                raise ValidationError(_('Satuan dasar tidak dapat diarsipkan. Buat kelompok satuan baru jika acuannya salah.'))
            critical_changed = any(
                ('managed_base_quantity' in values and float_compare(values['managed_base_quantity'], unit.managed_base_quantity, precision_digits=12) != 0)
                or ('rounding' in values and float_compare(values['rounding'], unit.rounding, precision_digits=12) != 0)
                or ('category_id' in values and values['category_id'] != unit.category_id.id)
                or ('uom_type' in values and values['uom_type'] != unit.uom_type)
                or ('factor' in values and float_compare(values['factor'], unit.factor, precision_digits=12) != 0)
                or ('factor_inv' in values and float_compare(values['factor_inv'], unit.factor_inv, precision_digits=12) != 0)
                for unit in self
            )
            if critical_changed and any(unit._managed_transaction_usage() for unit in self):
                raise ValidationError(_('Konversi dan kuantitas minimum tidak dapat diubah karena satuan sudah dipakai transaksi. Arsipkan satuan ini lalu buat satuan baru.'))
            if 'managed_base_quantity' in values:
                quantity = values.pop('managed_base_quantity')
                if quantity <= 0:
                    raise ValidationError(_('Nilai konversi harus lebih besar dari 0.'))
                values['factor'] = 1.0 / quantity
                values['uom_type'] = 'reference' if float_compare(quantity, 1.0, precision_digits=12) == 0 else 'bigger' if quantity > 1 else 'smaller'
        result = super().write(values)
        self._check_managed_duplicate_names()
        if self.env.context.get('managed_ui'):
            self.category_id._check_managed_structure()
        return result

    def unlink(self):
        if self.env.context.get('managed_ui'):
            raise ValidationError(_('Satuan tidak dapat dihapus. Arsipkan satuan yang tidak lagi digunakan.'))
        return super().unlink()

    def _check_managed_duplicate_names(self):
        if not self.env.context.get('managed_ui'):
            return
        Unit = self.with_context(active_test=False, managed_ui=False).sudo()
        for unit in self:
            if Unit.search_count([
                ('id', '!=', unit.id), ('category_id', '=', unit.category_id.id), ('name', '=ilike', unit.name),
            ]):
                raise ValidationError(_('Satuan %(name)s sudah ada pada kelompok %(category)s.', name=unit.name, category=unit.category_id.name))
