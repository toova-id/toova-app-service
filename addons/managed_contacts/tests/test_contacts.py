from odoo.tests.common import TransactionCase


class TestManagedContacts(TransactionCase):
    def test_contact_action_contract(self):
        contract = self.env['res.partner']._managed_ui_contract('managed_contacts.action_contact_persons')
        self.assertEqual(contract['list']['title'], 'Contact Persons')
        fields = {field['name'] for field in contract['form']['fields']}
        self.assertTrue({'parent_id', 'function', 'email', 'mobile'} <= fields)
