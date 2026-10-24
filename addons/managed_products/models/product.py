# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    managed_sku_normalized = fields.Char(compute='_compute_managed_sku', store=True, index=True)

    @api.depends('default_code')
    def _compute_managed_sku(self):
        for product in self:
            product.managed_sku_normalized = (product.default_code or '').strip().upper() or False

    def _check_managed_sku(self):
        if not self.env.context.get('managed_ui'):
            return
        Product = self.with_context(active_test=False, managed_ui=False).sudo()
        for product in self.filtered('managed_sku_normalized'):
            company_id = product.product_tmpl_id.company_id.id or self.env.company.id
            duplicate = Product.search([
                ('managed_sku_normalized', '=', product.managed_sku_normalized),
                ('id', '!=', product.id),
                ('product_tmpl_id.company_id', 'in', [False, company_id]),
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


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('managed_ui') and not self.env.company.managed_product_variants:
            for vals in vals_list:
                if vals.get('attribute_line_ids'):
                    raise ValidationError(_('Enable Product Variants before adding attributes.'))
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get('managed_ui') and vals.get('attribute_line_ids') and not self.env.company.managed_product_variants:
            raise ValidationError(_('Enable Product Variants before adding attributes.'))
        return super().write(vals)

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        supported = {
            'product.product_template_action', 'product.product_template_action_all',
            'account.product_product_action_sellable', 'account.product_product_action_purchasable',
            'sale.product_template_action', 'purchase.product_normal_action_puchased',
            'stock.product_template_action_product', 'mrp.product_template_action',
        }
        if action_xmlid not in supported:
            return super()._managed_ui_contract(action_xmlid)

        fields_by_name = self._fields
        def available(*names):
            return [name for name in names if name in fields_by_name]

        list_fields = available(
            'image_128', 'default_code', 'name', 'detailed_type',
            'categ_id', 'list_price', 'standard_price', 'uom_id',
            'qty_available', 'active',
        )
        form_fields = available(
            'image_1920', 'name', 'default_code', 'barcode',
            'detailed_type', 'sale_ok', 'purchase_ok', 'active',
            'categ_id', 'uom_id', 'uom_po_id',
            'list_price', 'standard_price', 'taxes_id', 'supplier_taxes_id',
            'l10n_id_product_code', 'tracking', 'responsible_id',
            'weight', 'volume', 'description_sale', 'description_purchase', 'description',
            'company_id', 'currency_id', 'qty_available', 'virtual_available',
        )
        readonly = {'currency_id', 'qty_available', 'virtual_available'}
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
                    {'name': name, **({'widget': 'image'} if name == 'image_1920' else {})}
                    for name in form_fields
                ],
                'write_fields': write_fields,
                'buttons': [],
            },
        }
