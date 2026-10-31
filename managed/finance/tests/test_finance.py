# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

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

    def test_accounting_sequences_use_document_codes_and_monthly_reset(self):
        self.env['account.move']._managed_configure_document_sequences()
        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        if not journal:
            self.skipTest('Sales journal is not configured.')
        expected = {
            'entry': 'JE2603000000',
            'out_invoice': 'INV2603000000',
            'out_receipt': 'INV2603000000',
            'out_refund': 'CN2603000000',
            'in_invoice': 'BILL2603000000',
            'in_receipt': 'BILL2603000000',
            'in_refund': 'DN2603000000',
        }
        for move_type, starting_sequence in expected.items():
            move = self.env['account.move'].new({
                'move_type': move_type, 'journal_id': journal.id,
                'company_id': journal.company_id.id, 'date': date(2026, 3, 1),
            })
            self.assertEqual(move._get_starting_sequence(), starting_sequence)
            self.assertEqual(move._deduce_sequence_number_reset(starting_sequence[:-6] + '000001'), 'month')
        inbound = self.env['account.move'].with_context(is_payment=True, default_payment_type='inbound').new({
            'move_type': 'entry', 'journal_id': journal.id, 'company_id': journal.company_id.id, 'date': date(2026, 3, 1),
        })
        outbound = inbound.with_context(default_payment_type='outbound')
        self.assertEqual(inbound._get_starting_sequence(), 'RCPT2603000000')
        self.assertEqual(outbound._get_starting_sequence(), 'PAY2603000000')

    def test_accounting_sequence_counters_are_separate_across_journals_and_types(self):
        journals = self.env['account.journal'].search([('type', '=', 'general'), ('company_id', '=', self.env.company.id)], limit=2)
        if len(journals) < 2:
            self.skipTest('Two general journals are required.')
        account = self.env['account.account'].search([('company_id', '=', self.env.company.id), ('deprecated', '=', False)], limit=1)
        if not account:
            self.skipTest('Accounting chart is not configured.')
        names = []
        for journal in journals:
            move = self.env['account.move'].create({
                'move_type': 'entry', 'journal_id': journal.id, 'date': date(2026, 3, 1),
                'line_ids': [(0, 0, {'name': 'Debit', 'account_id': account.id, 'debit': 1}),
                             (0, 0, {'name': 'Credit', 'account_id': account.id, 'credit': 1})],
            })
            move.action_post()
            names.append(move.name)
        self.assertEqual(names, ['JE2603000001', 'JE2603000002'])

    def test_finance_related_documents_use_native_reconciliation_and_sale_lines(self):
        invoice = self.env['account.move'].new({'move_type': 'out_invoice'})
        invoice_related = {item['key']: item for item in invoice._managed_related_documents()}
        self.assertEqual(invoice_related['sale_orders']['action_xmlid'], 'sales.action_orders')
        self.assertEqual(invoice_related['payments']['action_xmlid'], 'finance.action_payments')
        payment = self.env['account.payment'].new({'payment_type': 'inbound', 'partner_type': 'customer'})
        payment_related = {item['key']: item for item in payment._managed_related_documents()}
        self.assertEqual(payment_related['invoices']['action_xmlid'], 'finance.action_customer_invoices')
        self.assertEqual(payment_related['sale_orders']['action_xmlid'], 'sales.action_orders')

    def test_payment_contract_is_read_only(self):
        contract = self.env['account.payment']._managed_ui_contract('finance.action_payments')
        self.assertFalse(contract['list']['create'])
        self.assertFalse(contract['form']['write'])
        self.assertEqual(contract['form']['write_fields'], [])
