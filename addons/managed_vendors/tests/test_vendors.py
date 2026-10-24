from odoo.tests.common import TransactionCase


class TestManagedVendors(TransactionCase):
    def test_vendor_action_contract(self):
        contract = self.env['res.partner']._managed_ui_contract('managed_vendors.action_vendors')
        self.assertEqual(contract['list']['title'], 'Vendors')
