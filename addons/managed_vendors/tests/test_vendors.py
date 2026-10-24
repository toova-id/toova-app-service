from odoo.tests.common import TransactionCase


class TestManagedVendors(TransactionCase):
    def test_vendor_action_contract(self):
        contract = self.env['res.partner']._managed_ui_contract('managed_vendors.action_vendors')
        self.assertEqual(contract['list']['title'], 'Vendors')
        fields = {field['name']: field for field in contract['form']['fields']}
        self.assertEqual(fields['managed_address_ids']['widget'], 'managed_addresses')
        self.assertEqual(fields['child_ids']['widget'], 'managed_contacts')
        self.assertEqual(fields['bank_ids']['widget'], 'managed_bank_accounts')
