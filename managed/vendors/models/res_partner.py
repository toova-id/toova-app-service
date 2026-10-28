from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'vendors.action_vendors':
            return super()._managed_ui_contract(action_xmlid)
        return self._managed_profile_contract('vendor')


class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_permission_catalog(self):
        features = super()._managed_permission_catalog()
        permission = {'key': 'contacts.vendors', 'label': 'Vendors', 'groups': {'read': 'settings.group_contacts_vendors_read', 'write': 'settings.group_contacts_vendors_write'}}
        return [{**feature, 'permissions': [*feature['permissions'], permission]} if feature['key'] == 'contacts' else feature for feature in features]

    @api.model
    def _managed_action_permissions(self):
        return {**super()._managed_action_permissions(), 'vendors.action_vendors': 'contacts.vendors'}

    @api.model
    def _managed_menu_permissions(self):
        return {**super()._managed_menu_permissions(), 'vendors.menu_vendors_root': 'contacts.vendors'}
