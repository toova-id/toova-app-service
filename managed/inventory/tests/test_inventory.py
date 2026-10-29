# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        self.assertEqual(buttons, {'action_assign', 'button_validate', 'action_cancel'})
        self.assertIsNone(self.env['stock.picking']._managed_ui_contract('stock.unknown_action'))
