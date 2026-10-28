from odoo.tests.common import TransactionCase


class TestManagedPeople(TransactionCase):
    def test_employee_action_contract(self):
        contract = self.env['hr.employee']._managed_ui_contract('people.action_employees')
        self.assertEqual(contract['list']['title'], 'Employees')
