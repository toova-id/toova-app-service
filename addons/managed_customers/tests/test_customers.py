from odoo.tests.common import TransactionCase


class TestManagedCustomers(TransactionCase):
    def test_customer_action_contract(self):
        contract = self.env['res.partner']._managed_ui_contract('managed_customers.action_customers')
        self.assertEqual(contract['list']['title'], 'Customers')
