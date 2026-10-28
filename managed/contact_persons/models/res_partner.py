from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _managed_contact_domain(self):
        employee_partners = self.env['hr.employee'].sudo().search([]).mapped('work_contact_id')
        return [('id', 'not in', employee_partners.ids)]

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'contact_persons.action_contact_persons':
            return super()._managed_ui_contract(action_xmlid)
        fields_by_name = self._fields
        names = [name for name in ('image_1920', 'name', 'parent_id', 'function', 'email', 'phone', 'mobile', 'lang', 'comment', 'active') if name in fields_by_name]
        return {
            'list': {'title': 'Contact Persons', 'fields': [name for name in ('name', 'parent_id', 'function', 'email', 'mobile') if name in fields_by_name], 'default_order': 'parent_id, name'},
            'form': {'title': 'Contact Person', 'fields': [{'name': n, **({'widget': 'image'} if n == 'image_1920' else {})} for n in names], 'write_fields': names, 'buttons': []},
        }


class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_permission_catalog(self):
        features = super()._managed_permission_catalog()
        permission = {'key': 'contacts.contact_persons', 'label': 'Contact Persons', 'groups': {'read': 'settings.group_contacts_contact_persons_read', 'write': 'settings.group_contacts_contact_persons_write'}}
        return [{**feature, 'permissions': [*feature['permissions'], permission]} if feature['key'] == 'contacts' else feature for feature in features]

    @api.model
    def _managed_action_permissions(self):
        return {**super()._managed_action_permissions(), 'contact_persons.action_contact_persons': 'contacts.contact_persons'}

    @api.model
    def _managed_menu_permissions(self):
        return {**super()._managed_menu_permissions(), 'contact_persons.menu_contact_persons_root': 'contacts.contact_persons'}
