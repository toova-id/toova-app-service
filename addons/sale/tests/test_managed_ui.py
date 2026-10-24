# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestSaleManagedUiContract(TransactionCase):

    def test_sale_order_contract_does_not_depend_on_xml_views(self):
        contract = self.env['sale.order']._managed_ui_contract('sale.action_orders')
        self.assertEqual(contract['list']['fields'][0], 'name')
        self.assertIn('order_line', [field if isinstance(field, str) else field['name'] for field in contract['form']['fields']])
        self.assertNotIn('amount_total', contract['form']['write_fields'])
        self.assertIsNone(self.env['sale.order']._managed_ui_contract('sale.unknown_action'))
