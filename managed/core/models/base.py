# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Base(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        return None

    @api.model
    def _managed_apply_company_default(self, values):
        """Managed tenant owns company selection; users never choose it."""
        field = self._fields.get('company_id')
        if not field or field.type != 'many2one' or field.comodel_name != 'res.company' or field.related or field.compute:
            return values
        return {**values, 'company_id': self.env.company.id}

    @api.model
    def _managed_action_permission(self, action_xmlid):
        return self.env['managed.settings.registry']._managed_registry()['actions'].get(action_xmlid)

    @api.model
    def _managed_menu_permission(self, menu_xmlid):
        return self.env['managed.settings.registry']._managed_registry()['menus'].get(menu_xmlid)
