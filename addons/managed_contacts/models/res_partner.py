from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _managed_contact_domain(self):
        employee_partners = self.env['hr.employee'].sudo().search([]).mapped('work_contact_id')
        return [('id', 'not in', employee_partners.ids)]

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'managed_contacts.action_contact_persons':
            return super()._managed_ui_contract(action_xmlid)
        fields_by_name = self._fields
        names = [name for name in ('image_1920', 'name', 'parent_id', 'function', 'email', 'phone', 'mobile', 'lang', 'comment', 'active') if name in fields_by_name]
        return {
            'list': {'title': 'Contact Persons', 'fields': [name for name in ('name', 'parent_id', 'function', 'email', 'mobile') if name in fields_by_name], 'default_order': 'parent_id, name'},
            'form': {'title': 'Contact Person', 'fields': [{'name': n, **({'widget': 'image'} if n == 'image_1920' else {})} for n in names], 'write_fields': names, 'buttons': []},
        }
