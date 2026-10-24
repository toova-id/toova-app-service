# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestManagedProducts(TransactionCase):

    def test_sku_normalization_and_duplicate_block(self):
        first = self.env['product.product'].with_context(managed_ui=True).create({'name': 'First', 'default_code': ' sku-001 '})
        self.assertEqual(first.managed_sku_normalized, 'SKU-001')
        with self.assertRaises(ValidationError):
            self.env['product.product'].with_context(managed_ui=True).create({'name': 'Duplicate', 'default_code': 'SKU-001'})

    def test_product_contract(self):
        contract = self.env['product.template']._managed_ui_contract('sale.product_template_action')
        self.assertIn('default_code', [field if isinstance(field, str) else field['name'] for field in contract['form']['fields']])
        self.assertNotIn('qty_available', contract['form']['write_fields'])
