# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestManagedDirectory(TransactionCase):

    def test_identity_and_roles(self):
        partner = self.env['res.partner'].with_context(managed_ui=True, managed_party_role='customer').create({
            'name': 'First', 'mobile': '0812-3456-7890', 'vat': '12.345.678.9-012.000',
        })
        self.assertEqual(partner.managed_phone_normalized, '6281234567890')
        self.assertEqual(partner.managed_vat_normalized, '123456789012000')
        self.assertEqual(partner.managed_role_ids.role, 'customer')
        with self.assertRaises(ValidationError):
            self.env['res.partner'].with_context(managed_ui=True).create({'name': 'Duplicate', 'vat': '123456789012000'})
