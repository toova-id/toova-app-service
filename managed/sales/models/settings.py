# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_settings_sections(self):
        return [
            *super()._managed_settings_sections(),
            {'key': 'sales', 'placement': 'advanced', 'label': 'Penjualan', 'description': 'Default penawaran, konfirmasi, dan penagihan.', 'icon': 'hand-coins', 'sequence': 40, 'permission': 'settings.sales', 'provider': 'managed.sales.settings'},
        ]

    @api.model
    def _managed_permission_catalog(self):
        return [
            *super()._managed_permission_catalog(),
            {'key': 'sales', 'label': 'Sales', 'sequence': 40, 'permissions': [
                {'key': 'sales.quotations', 'label': 'Quotations', 'groups': {'read': 'settings.group_sales_quotations_read', 'write': 'settings.group_sales_quotations_write'}},
                {'key': 'sales.orders', 'label': 'Sales Orders', 'groups': {'read': 'settings.group_sales_orders_read', 'write': 'settings.group_sales_orders_write'}},
                {'key': 'settings.sales', 'label': 'Sales Settings', 'groups': {'read': 'settings.group_settings_sales_read', 'write': 'settings.group_settings_sales_write'}},
            ]},
        ]

    @api.model
    def _managed_action_permissions(self):
        return {
            **super()._managed_action_permissions(),
            'sale.action_quotations': 'sales.quotations',
            'sale.action_quotations_with_onboarding': 'sales.quotations',
            'sale.action_orders': 'sales.orders',
            'sale.action_orders_to_invoice': 'sales.orders',
            'sale.action_orders_upselling': 'sales.orders',
        }


class ManagedSalesSettings(models.AbstractModel):
    _name = 'managed.sales.settings'
    _description = 'Managed Sales Settings Provider'

    @api.model
    def _config(self):
        fields_list = [
            'default_invoice_policy', 'group_auto_done_setting', 'use_quotation_validity_days',
            'quotation_validity_days', 'portal_confirmation_sign', 'portal_confirmation_pay',
            'deposit_default_product_id', 'invoice_mail_template_id',
        ]
        return self.env['res.config.settings'].sudo().create(
            self.env['res.config.settings'].sudo().default_get(fields_list)
        ), fields_list

    @api.model
    def get_values(self):
        config, fields_list = self._config()
        values = config.read(fields_list)[0]
        config.unlink()
        return values

    @api.model
    def save_values(self, values):
        fields_list = {
            'default_invoice_policy', 'group_auto_done_setting', 'use_quotation_validity_days',
            'quotation_validity_days', 'portal_confirmation_sign', 'portal_confirmation_pay',
            'deposit_default_product_id', 'invoice_mail_template_id',
        }
        unknown = set(values) - fields_list
        if unknown:
            raise ValidationError(_('Field pengaturan penjualan tidak diizinkan: %(fields)s', fields=', '.join(sorted(unknown))))
        normalized = dict(values)
        for name in ('deposit_default_product_id', 'invoice_mail_template_id'):
            value = normalized.get(name)
            if isinstance(value, (list, tuple)):
                normalized[name] = value[0] if value else False
        config, _read_fields = self._config()
        config.write(normalized)
        config.set_values()
        result = config.read(list(fields_list))[0]
        config.unlink()
        return result

    @api.model
    def get_readiness(self):
        company = self.env.company
        ready = bool(company.quotation_validity_days and self.env['product.pricelist'].search_count([]))
        return {'status': 'ready' if ready else 'warning', 'message': None if ready else 'Lengkapi masa berlaku atau pricelist'}
