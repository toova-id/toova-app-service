# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

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
        columns = {column['name'] for column in fields['order_line']['relation']['columns']}
        self.assertIn('price_total', columns)
        self.assertIn('managed_discount_mode', columns)
        self.assertIn('managed_discount_fixed', columns)
        self.assertIn('picking_ids', fields)
        self.assertIn('invoice_ids', fields)
        self.assertNotIn('amount_total', contract['form']['write_fields'])

    def test_sales_order_sequence_uses_monthly_industry_format(self):
        sequence = self.env['sale.order']._managed_configure_document_sequence()
        first = sequence.next_by_id(sequence_date=datetime(2026, 3, 1))
        second = sequence.next_by_id(sequence_date=datetime(2026, 3, 31))
        april = sequence.next_by_id(sequence_date=datetime(2026, 4, 1))
        self.assertEqual(first, 'SO2603000001')
        self.assertEqual(second, 'SO2603000002')
        self.assertEqual(april, 'SO2604000001')

    def test_fixed_discount_uses_native_percentage_engine(self):
        product = self.env.ref('product.product_product_4')
        line = self.env['sale.order.line'].with_context(managed_ui=True).new({
            'product_id': product.id, 'product_uom_qty': 2, 'price_unit': 100000,
            'managed_discount_mode': 'fixed', 'managed_discount_fixed': 30000,
        })
        line._onchange_managed_fixed_discount()
        self.assertEqual(line.discount, 15)

    def test_orders_cannot_be_created_from_order_action(self):
        contract = self.env['sale.order']._managed_ui_contract('sales.action_orders')
        self.assertFalse(contract['list']['create'])
        self.assertFalse(contract['form']['create'])
        self.assertFalse(contract['form']['write'])
        self.assertIn('action_create_managed_invoice', {button['name'] for button in contract['form']['buttons']})
        self.assertIsNone(self.env['sale.order']._managed_ui_contract('sale.unknown_action'))

    def test_managed_sale_rejects_non_customer(self):
        partner = self.env['res.partner'].create({'name': 'Bukan customer'})
        product = self.env['product.product'].create({'name': 'Produk jual'})
        with self.assertRaises(ValidationError):
            self.env['sale.order'].with_context(managed_ui=True).create({
                'partner_id': partner.id,
                'order_line': [(0, 0, {'product_id': product.id, 'product_uom_qty': 1})],
            })
