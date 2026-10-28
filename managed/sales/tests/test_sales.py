# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestSaleManagedUiContract(TransactionCase):

    def test_quotation_contract_uses_managed_action_and_variant_lines(self):
        contract = self.env['sale.order']._managed_ui_contract('sales.action_quotations')
        fields = {field['name']: field for field in contract['form']['fields']}
        self.assertEqual(contract['list']['title'], 'Penawaran')
        self.assertTrue(contract['list']['create'])
        self.assertEqual(fields['partner_id']['widget'], 'managed_customer_many2one')
        self.assertEqual(fields['order_line']['widget'], 'managed_sale_order_lines')
        self.assertEqual(fields['order_line']['relation']['columns'][0]['name'], 'product_id')
        self.assertEqual(fields['order_line']['relation']['columns'][0]['widget'], 'managed_sale_product_many2one')
        self.assertNotIn('amount_total', contract['form']['write_fields'])

    def test_orders_cannot_be_created_from_order_action(self):
        contract = self.env['sale.order']._managed_ui_contract('sales.action_orders')
        self.assertFalse(contract['list']['create'])
        self.assertFalse(contract['form']['create'])
        self.assertFalse(contract['form']['write'])
        self.assertIsNone(self.env['sale.order']._managed_ui_contract('sale.unknown_action'))

    def test_managed_sale_rejects_non_customer(self):
        partner = self.env['res.partner'].create({'name': 'Bukan customer'})
        product = self.env['product.product'].create({'name': 'Produk jual'})
        with self.assertRaises(ValidationError):
            self.env['sale.order'].with_context(managed_ui=True).create({
                'partner_id': partner.id,
                'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 1})],
            })
