# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestManagedFinance(TransactionCase):

    def test_customer_invoice_contract_uses_native_account_move(self):
        contract = self.env['account.move']._managed_ui_contract('finance.action_customer_invoices')
        fields = {field['name']: field for field in contract['form']['fields']}
        buttons = {button['name'] for button in contract['form']['buttons']}
        self.assertFalse(contract['list']['create'])
        self.assertFalse(contract['list']['delete'])
        self.assertNotIn('amount_total', contract['form']['write_fields'])
        self.assertEqual(fields['invoice_line_ids']['relation']['columns'][0]['name'], 'product_id')
        self.assertEqual(buttons, {'action_post', 'action_register_payment', 'button_cancel'})
        self.assertIsNone(self.env['account.move']._managed_ui_contract('account.unknown_action'))

    def test_payment_contract_is_read_only(self):
        contract = self.env['account.payment']._managed_ui_contract('finance.action_payments')
        self.assertFalse(contract['list']['create'])
        self.assertFalse(contract['form']['write'])
        self.assertEqual(contract['form']['write_fields'], [])
