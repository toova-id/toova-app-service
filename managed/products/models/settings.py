# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_settings_sections(self):
        return [
            *super()._managed_settings_sections(),
            {'key': 'products', 'placement': 'advanced', 'label': 'Produk', 'description': 'Default katalog dan kesiapan produk.', 'icon': 'boxes', 'sequence': 50, 'permission': 'settings.products', 'provider': 'managed.products.settings'},
        ]

    @api.model
    def _managed_permission_catalog(self):
        return [
            *super()._managed_permission_catalog(),
            {'key': 'products', 'label': 'Products', 'sequence': 20, 'permissions': [
                {'key': 'products.products', 'label': 'Products', 'groups': {'read': 'settings.group_products_products_read', 'write': 'settings.group_products_products_write'}},
                {'key': 'products.attributes', 'label': 'Attributes', 'groups': {'read': 'settings.group_products_attributes_read', 'write': 'settings.group_products_attributes_write'}},
                {'key': 'products.categories', 'label': 'Categories', 'groups': {'read': 'settings.group_products_categories_read', 'write': 'settings.group_products_categories_write'}},
                {'key': 'products.pricelists', 'label': 'Pricelists', 'groups': {'read': 'settings.group_products_pricelists_read', 'write': 'settings.group_products_pricelists_write'}},
                {'key': 'products.uom', 'label': 'Units of Measure', 'groups': {'read': 'settings.group_products_uom_read', 'write': 'settings.group_products_uom_write'}},
                {'key': 'settings.products', 'label': 'Product Settings', 'groups': {'read': 'settings.group_settings_products_read', 'write': 'settings.group_settings_products_write'}},
            ]},
        ]

    @api.model
    def _managed_action_permissions(self):
        return {
            **super()._managed_action_permissions(),
            'products.action_products': 'products.products',
            'products.action_product_attributes': 'products.attributes',
            'products.action_product_categories': 'products.categories',
            'products.action_product_pricelists': 'products.pricelists',
            'products.action_uom_categories': 'products.uom',
        }

    @api.model
    def _managed_menu_permissions(self):
        return {
            **super()._managed_menu_permissions(),
            'products.menu_products': 'products.products',
            'products.menu_product_attributes': 'products.attributes',
            'products.menu_product_categories': 'products.categories',
            'products.menu_product_pricelists': 'products.pricelists',
            'products.menu_product_uom': 'products.uom',
        }


class ManagedProductsSettings(models.AbstractModel):
    _name = 'managed.products.settings'
    _description = 'Managed Product Settings Provider'

    @api.model
    def get_values(self):
        Product = self.env['product.template']
        fields_list = Product.default_get(['categ_id', 'uom_id', 'uom_po_id', 'invoice_policy'])
        return {
            'defaultCategory': fields_list.get('categ_id') or False,
            'defaultUom': fields_list.get('uom_id') or False,
            'defaultPurchaseUom': fields_list.get('uom_po_id') or False,
            'invoicePolicy': fields_list.get('invoice_policy') or 'order',
        }

    @api.model
    def save_values(self, values):
        allowed = {key: values[key] for key in ('defaultCategory', 'defaultUom', 'defaultPurchaseUom', 'invoicePolicy') if key in values}
        IrDefault = self.env['ir.default'].sudo()
        mapping = {'defaultCategory': 'categ_id', 'defaultUom': 'uom_id', 'defaultPurchaseUom': 'uom_po_id', 'invoicePolicy': 'invoice_policy'}
        for key, value in allowed.items():
            IrDefault.set('product.template', mapping[key], value or False, company_id=self.env.company.id)
        return self.get_values()

    @api.model
    def get_readiness(self):
        missing_codes = self.env['product.template'].search_count([('active', '=', True), ('l10n_id_product_code', '=', False)]) if 'l10n_id_product_code' in self.env['product.template']._fields else 0
        return {'status': 'warning' if missing_codes else 'ready', 'message': f'{missing_codes} produk tanpa kode Coretax' if missing_codes else None}
