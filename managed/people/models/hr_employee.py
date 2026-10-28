from odoo import api, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'people.action_employees':
            return super()._managed_ui_contract(action_xmlid)
        available = self._fields
        list_fields = [n for n in ('name', 'job_id', 'department_id', 'work_email', 'work_phone', 'company_id') if n in available]
        form_fields = [n for n in (
            'image_1920', 'name', 'job_id', 'department_id', 'parent_id', 'coach_id', 'work_location_id',
            'work_email', 'work_phone', 'mobile_phone', 'user_id', 'address_home_id', 'private_email', 'phone',
            'identification_id', 'passport_id', 'birthday', 'gender', 'marital', 'emergency_contact', 'emergency_phone',
            'bank_account_id', 'barcode', 'category_ids', 'notes', 'company_id', 'active',
        ) if n in available]
        return {
            'list': {'title': 'Employees', 'fields': list_fields, 'default_order': 'name asc'},
            'form': {'title': 'Employee', 'fields': [{'name': n, **({'widget': 'image'} if n == 'image_1920' else {})} for n in form_fields], 'write_fields': form_fields, 'buttons': []},
        }


class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_permission_catalog(self):
        return [
            *super()._managed_permission_catalog(),
            {'key': 'people', 'label': 'People', 'sequence': 30, 'permissions': [
                {'key': 'people.employees', 'label': 'Employees', 'groups': {'read': 'settings.group_people_employees_read', 'write': 'settings.group_people_employees_write'}},
            ]},
        ]

    @api.model
    def _managed_action_permissions(self):
        return {**super()._managed_action_permissions(), 'people.action_employees': 'people.employees'}

    @api.model
    def _managed_menu_permissions(self):
        return {**super()._managed_menu_permissions(), 'people.menu_employees_root': 'people.employees'}
