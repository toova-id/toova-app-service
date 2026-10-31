# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import TransactionCase


class TestManagedInventory(TransactionCase):

    def test_delivery_contract_uses_native_picking_workflow(self):
        contract = self.env['stock.picking']._managed_ui_contract('inventory.action_deliveries')
        fields = {field['name']: field for field in contract['form']['fields']}
        buttons = {button['name'] for button in contract['form']['buttons']}
        self.assertFalse(contract['list']['create'])
        self.assertFalse(contract['list']['delete'])
        self.assertEqual(fields['managed_move_line_ids']['widget'], 'managed_stock_move_lines')
        self.assertEqual(fields['managed_move_line_ids']['relation']['columns'][0]['name'], 'product_id')
        self.assertEqual(buttons, {
            'action_assign', 'action_set_quantities_to_reservation',
            'action_clear_quantities_to_zero', 'button_validate', 'action_cancel',
        })
        self.assertIsNone(self.env['stock.picking']._managed_ui_contract('stock.unknown_action'))

    def test_delivery_related_document_uses_native_sale_relation(self):
        picking = self.env['stock.picking'].new({})
        related = picking._managed_related_documents()
        self.assertEqual(related[0]['action_xmlid'], 'sales.action_orders')
        self.assertEqual(related[0]['records'], picking.sale_id)

    def test_operation_summary_uses_native_state_and_quantities(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        picking = self.env['stock.picking'].new({
            'picking_type_id': warehouse.out_type_id.id,
            'state': 'assigned',
            'move_ids': [(0, 0, {
                'name': 'Test', 'product_id': self.env.ref('product.product_product_4').id,
                'product_uom_qty': 5, 'quantity_done': 2,
                'product_uom': self.env.ref('uom.product_uom_unit').id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            })],
        })
        self.assertEqual(picking.managed_operation_kind, 'Pengiriman')
        self.assertEqual(picking.managed_operation_status, 'Siap diproses')
        self.assertEqual(picking.managed_operation_progress, '2.0 dari 5.0 unit')

    def test_stock_sequences_use_operation_codes_and_monthly_reset(self):
        picking_types = self.env['stock.picking.type']._managed_configure_document_sequences()
        purchase_sequence = self.env.ref('purchase.seq_purchase_order')
        self.assertEqual(purchase_sequence.next_by_id(sequence_date=datetime(2026, 3, 1)), 'PO2603000001')
        picking_types = picking_types.with_context(active_test=False)
        for operation, code in (('outgoing', 'DO'), ('incoming', 'GR'), ('internal', 'ST')):
            operation_types = picking_types.filtered(lambda item: item.code == operation and item.sequence_code != 'RET')
            self.assertTrue(operation_types)
            self.assertEqual(set(operation_types.mapped('_managed_document_code')), {code})
            sequences = operation_types.mapped('sequence_id')
            self.assertEqual(len(sequences), 1)
            self.assertEqual(sequences.next_by_id(sequence_date=datetime(2026, 3, 1)), f'{code}2603000001')
            self.assertEqual(sequences.next_by_id(sequence_date=datetime(2026, 4, 1)), f'{code}2604000001')
        return_type = picking_types.filtered(lambda item: item.sequence_code == 'RET')[:1]
        self.assertEqual(return_type._managed_document_code(), 'RTN')

    def test_return_wizard_uses_return_document_sequence(self):
        self.env['stock.picking.type']._managed_configure_document_sequences()
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        picking = self.env['stock.picking'].new({
            'name': 'DO2603000001', 'picking_type_id': warehouse.out_type_id.id,
            'company_id': self.env.company.id, 'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        values = self.env['stock.return.picking'].new({'picking_id': picking})._prepare_picking_default_values()
        self.assertTrue(values['name'].startswith('RTN'))
        self.assertEqual(len(values['name']), 13)
