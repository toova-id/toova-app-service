# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestManagedProducts(TransactionCase):

    def test_sku_normalization_and_duplicate_block(self):
        first = self.env['product.product'].with_context(managed_ui=True).create({'name': 'First', 'default_code': ' sku-001 '})
        self.assertEqual(first.managed_sku_normalized, 'SKU-001')
        with self.assertRaises(ValidationError):
            self.env['product.product'].with_context(managed_ui=True).create({'name': 'Duplicate', 'default_code': 'SKU-001'})

    def test_sku_can_repeat_across_company_specific_catalogs(self):
        company = self.env['res.company'].create({'name': 'Other Product Company'})
        self.env['product.template'].with_context(managed_ui=True).create({
            'name': 'Main Company Product', 'default_code': 'COMPANY-SKU',
            'company_id': self.env.company.id,
        })
        other = self.env['product.template'].with_company(company).with_context(managed_ui=True).create({
            'name': 'Other Company Product', 'default_code': 'COMPANY-SKU',
            'company_id': company.id,
        })
        self.assertEqual(other.default_code, 'COMPANY-SKU')

    def test_managed_product_kind_defaults_from_native_type(self):
        defaults = self.env['product.template'].default_get([
            'managed_product_kind', 'managed_track_inventory', 'detailed_type',
        ])
        self.assertEqual(defaults['managed_product_kind'], 'goods')
        self.assertFalse(defaults['managed_track_inventory'])

    def test_managed_product_kind_maps_to_native_type(self):
        product = self.env['product.template'].with_context(managed_ui=True).create({
            'name': 'Managed Goods', 'managed_product_kind': 'goods',
            'managed_track_inventory': True,
        })
        self.assertEqual(product.detailed_type, 'product')
        product.write({'managed_track_inventory': False})
        self.assertEqual(product.detailed_type, 'consu')
        product.write({'managed_product_kind': 'service'})
        self.assertEqual(product.detailed_type, 'service')

    def test_product_contract(self):
        contract = self.env['product.template']._managed_ui_contract('managed_products.action_products')
        fields = {field if isinstance(field, str) else field['name']: field for field in contract['form']['fields']}
        self.assertIn('default_code', fields)
        self.assertIn('managed_product_kind', fields)
        self.assertIn('managed_track_inventory', fields)
        self.assertEqual(fields['default_code']['label'], 'SKU')
        self.assertEqual(fields['seller_ids']['widget'], 'managed_supplier_prices')
        self.assertIn('property_account_income_id', fields)
        self.assertNotIn('qty_available', contract['form']['write_fields'])

    def test_vendor_price_uses_native_supplierinfo(self):
        vendor = self.env['res.partner'].create({'name': 'Managed Vendor', 'supplier_rank': 1})
        product = self.env['product.template'].with_context(managed_ui=True).create({
            'name': 'Managed Product', 'default_code': 'PRODUCT-001',
            'seller_ids': [(0, 0, {
                'partner_id': vendor.id, 'product_code': 'VENDOR-001',
                'min_qty': 5, 'price': 12000, 'delay': 3,
            })],
        })
        self.assertEqual(product.seller_ids.partner_id, vendor)
        self.assertEqual(product.seller_ids.product_code, 'VENDOR-001')
        self.assertEqual(product.seller_ids.min_qty, 5)
