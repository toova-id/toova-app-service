from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'managed_vendors.action_vendors':
            return super()._managed_ui_contract(action_xmlid)
        return self._managed_profile_contract('vendor')
