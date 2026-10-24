# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestManagedContacts(TransactionCase):

    def test_identity_normalization_and_duplicate_block(self):
        self.env['res.partner'].with_context(managed_ui=True).create({'name': 'First', 'mobile': '0812-3456-7890', 'vat': '12.345.678.9-012.000'})
        partner = self.env['res.partner'].search([('name', '=', 'First')])
        self.assertEqual(partner.managed_phone_normalized, '6281234567890')
        self.assertEqual(partner.managed_vat_normalized, '123456789012000')
        with self.assertRaises(ValidationError):
            self.env['res.partner'].with_context(managed_ui=True).create({'name': 'Duplicate', 'vat': '123456789012000'})

    def test_contact_contract(self):
        contract = self.env['res.partner']._managed_ui_contract('contacts.action_contacts')
        self.assertIn('name', contract['list']['fields'])
        self.assertIn('vat', contract['form']['write_fields'])
