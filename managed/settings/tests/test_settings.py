# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestManagedSettings(TransactionCase):

    def test_registry_collects_module_contributions(self):
        registry = self.env['managed.settings.registry']._managed_registry()
        self.assertIn('sales', [section['key'] for section in registry['sections']])
        self.assertIn('products', [section['key'] for section in registry['sections']])
        self.assertIn('contacts.customers', registry['permissions'])
        self.assertEqual(registry['actions']['products.action_products'], 'products.products')

    def test_administrator_bootstrap(self):
        admin = self.env.ref('base.user_admin')
        self.assertEqual(admin._managed_permission_level('settings.users'), 'write')
        self.assertEqual(admin._managed_permission_level('products.products'), 'write')
        self.assertEqual(admin.company_ids, self.env.company)

    def test_roles_merge_highest_permission(self):
        user = self.env['res.users'].create({
            'name': 'Role Test', 'login': 'role-test',
            'company_id': self.env.company.id, 'company_ids': [(6, 0, [self.env.company.id])],
        })
        viewer = self.env['managed.settings.role'].with_context(managed_settings_bootstrap=True).create({
            'name': 'Viewer',
            'grant_ids': [(0, 0, {'permission_key': 'products.products', 'level': 'read'})],
        })
        editor = self.env['managed.settings.role'].with_context(managed_settings_bootstrap=True).create({
            'name': 'Editor',
            'grant_ids': [(0, 0, {'permission_key': 'products.products', 'level': 'write'})],
        })
        user.with_context(managed_settings_bootstrap=True).write({'managed_role_ids': [(6, 0, (viewer | editor).ids)]})
        self.assertEqual(user._managed_permission_level('products.products'), 'write')
        self.assertTrue(user.has_group('settings.group_products_products_write'))

    def test_last_administrator_cannot_be_removed(self):
        administrator = self.env['managed.settings.role'].search([('name', '=', 'Tenant Administrator')], limit=1)
        with self.assertRaises(ValidationError):
            administrator.write({'active': False})

    def test_company_profile_is_singleton(self):
        profile = self.env['managed.settings.company'].search([])
        self.assertEqual(profile.company_id, self.env.company)
        with self.assertRaises(Exception):
            self.env['managed.settings.company'].create({'company_id': self.env.company.id})
