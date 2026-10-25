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

    def test_attribute_contract(self):
        contract = self.env['product.attribute']._managed_ui_contract('managed_products.action_product_attributes')
        fields = {field if isinstance(field, str) else field['name']: field for field in contract['form']['fields']}
        self.assertEqual(fields['value_ids']['widget'], 'managed_attribute_values')
        self.assertEqual([column if isinstance(column, str) else column['name'] for column in fields['value_ids']['relation']['columns']], ['name', 'html_color', 'is_custom', 'sequence'])
        self.assertEqual(fields['name']['label'], 'Nama atribut')
        self.assertEqual(fields['display_type']['selection'][-1], ('color', 'Pilihan warna'))
        self.assertIn('value_ids', contract['form']['write_fields'])

    def test_attribute_names_are_trimmed_and_duplicates_blocked(self):
        attribute = self.env['product.attribute'].with_context(managed_ui=True).create({
            'name': ' Isi kemasan ',
            'value_ids': [(0, 0, {'name': ' 250 ml '})],
        })
        self.assertEqual(attribute.name, 'Isi kemasan')
        self.assertEqual(attribute.value_ids.name, '250 ml')
        with self.assertRaises(ValidationError):
            self.env['product.attribute'].with_context(managed_ui=True).create({'name': 'isi KEMASAN'})
        with self.assertRaises(ValidationError):
            self.env['product.attribute.value'].with_context(managed_ui=True).create({
                'attribute_id': attribute.id, 'name': '250 ML',
            })

    def test_packaging_volume_values_generate_native_variants(self):
        self.env.company.managed_product_variants = True
        attribute = self.env['product.attribute'].with_context(managed_ui=True).create({
            'name': 'Isi kemasan',
            'value_ids': [(0, 0, {'name': '250 ml'}), (0, 0, {'name': '500 ml'}), (0, 0, {'name': '1 L'})],
        })
        product = self.env['product.template'].with_context(managed_ui=True).create({
            'name': 'Sabun cair',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            })],
        })
        self.assertEqual(product.product_variant_count, 3)
        self.assertEqual(set(product.product_variant_ids.mapped('managed_variant_name')), {'250 ml', '500 ml', '1 L'})

    def test_product_contract(self):
        contract = self.env['product.template']._managed_ui_contract('managed_products.action_products')
        fields = {field if isinstance(field, str) else field['name']: field for field in contract['form']['fields']}
        self.assertIn('default_code', fields)
        self.assertIn('managed_product_kind', fields)
        self.assertIn('managed_track_inventory', fields)
        self.assertEqual(fields['default_code']['label'], 'SKU')
        self.assertEqual(fields['attribute_line_ids']['widget'], 'managed_attribute_lines')
        self.assertEqual(fields['product_variant_ids']['widget'], 'managed_variants')
        self.assertEqual(fields['seller_ids']['widget'], 'managed_supplier_prices')
        self.assertIn('property_account_income_id', fields)
        self.assertNotIn('qty_available', contract['form']['write_fields'])

    def test_category_contract_and_duplicate_sibling_block(self):
        contract = self.env['product.category']._managed_ui_contract('managed_products.action_product_categories')
        fields = {field if isinstance(field, str) else field['name']: field for field in contract['form']['fields']}
        self.assertEqual(fields['name']['label'], 'Nama kategori')
        self.assertFalse(contract['list']['delete'])
        parent = self.env['product.category'].with_context(managed_ui=True).create({'name': ' Minuman '})
        self.assertEqual(parent.name, 'Minuman')
        self.env['product.category'].with_context(managed_ui=True).create({'name': 'Teh', 'parent_id': parent.id})
        with self.assertRaises(ValidationError):
            self.env['product.category'].with_context(managed_ui=True).create({'name': ' teh ', 'parent_id': parent.id})

    def test_pricelist_contract_and_native_rule(self):
        contract = self.env['product.pricelist']._managed_ui_contract('managed_products.action_product_pricelists')
        fields = {field if isinstance(field, str) else field['name']: field for field in contract['form']['fields']}
        self.assertEqual(fields['item_ids']['widget'], 'managed_pricelist_rules')
        self.assertIn('item_ids', contract['form']['write_fields'])
        self.assertFalse(contract['list']['delete'])
        product = self.env['product.product'].create({'name': 'Managed Price Product', 'list_price': 100000})
        pricelist = self.env['product.pricelist'].with_context(managed_ui=True).create({
            'name': ' Retail IDR ',
            'currency_id': self.env.company.currency_id.id,
            'item_ids': [(0, 0, {
                'applied_on': '1_product', 'product_tmpl_id': product.product_tmpl_id.id,
                'compute_price': 'fixed', 'fixed_price': 75000, 'min_quantity': 2,
            })],
        })
        self.assertEqual(pricelist.name, 'Retail IDR')
        self.assertEqual(pricelist.item_ids.product_tmpl_id, product.product_tmpl_id)
        self.assertEqual(pricelist._get_product_price(product, 2), 75000)
        with self.assertRaises(ValidationError):
            self.env['product.pricelist'].with_context(managed_ui=True).create({
                'name': 'retail idr', 'currency_id': self.env.company.currency_id.id,
            })

    def test_uom_contract_and_native_conversion(self):
        contract = self.env['uom.category']._managed_ui_contract('managed_products.action_uom_categories')
        fields = {field if isinstance(field, str) else field['name']: field for field in contract['form']['fields']}
        self.assertEqual(fields['uom_ids']['widget'], 'managed_uom_units')
        self.assertFalse(contract['list']['delete'])
        category = self.env['uom.category'].with_context(managed_ui=True).create({
            'name': ' Test Volume ',
            'uom_ids': [
                (0, 0, {'name': ' L ', 'managed_base_quantity': 1, 'rounding': 0.001}),
                (0, 0, {'name': ' ml ', 'managed_base_quantity': 0.001, 'rounding': 1}),
            ],
        })
        liter = category.uom_ids.filtered(lambda unit: unit.name == 'L')
        milliliter = category.uom_ids.filtered(lambda unit: unit.name == 'ml')
        self.assertEqual(category.name, 'Test Volume')
        self.assertEqual(liter.uom_type, 'reference')
        self.assertEqual(milliliter.uom_type, 'smaller')
        self.assertEqual(milliliter._compute_quantity(1000, liter), 1)
        with self.assertRaises(ValidationError):
            self.env['uom.uom'].with_context(managed_ui=True).create({
                'name': 'ML', 'category_id': category.id, 'managed_base_quantity': 0.001, 'rounding': 1,
            })

    def test_native_variant_generation_and_value_prices(self):
        self.env.company.managed_product_variants = True
        attribute = self.env['product.attribute'].create({'name': 'Managed Size', 'create_variant': 'always'})
        small, large = self.env['product.attribute.value'].create([
            {'name': 'S', 'attribute_id': attribute.id},
            {'name': 'L', 'attribute_id': attribute.id},
        ])
        product = self.env['product.template'].with_context(managed_ui=True).create({
            'name': 'Managed Shirt',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, [small.id, large.id])],
            })],
        })
        self.assertEqual(product.product_variant_count, 2)
        line = product.attribute_line_ids
        line.managed_value_prices = {str(small.id): 0, str(large.id): 15000}
        line._inverse_managed_value_prices()
        self.assertEqual(
            line.product_template_value_ids.filtered(lambda value: value.product_attribute_value_id == large).price_extra,
            15000,
        )
        variant = product.product_variant_ids.filtered(
            lambda item: large in item.product_template_attribute_value_ids.product_attribute_value_id
        )
        variant.with_context(managed_ui=True).write({'default_code': 'SHIRT-L', 'barcode': '9876543210123'})
        self.assertEqual(variant.managed_variant_name, 'L')

    def test_vendor_price_can_target_variant(self):
        self.env.company.managed_product_variants = True
        attribute = self.env['product.attribute'].create({'name': 'Managed Color', 'create_variant': 'always'})
        black, white = self.env['product.attribute.value'].create([
            {'name': 'Black', 'attribute_id': attribute.id},
            {'name': 'White', 'attribute_id': attribute.id},
        ])
        vendor = self.env['res.partner'].create({'name': 'Variant Vendor', 'supplier_rank': 1})
        product = self.env['product.template'].with_context(managed_ui=True).create({
            'name': 'Variant Product',
            'attribute_line_ids': [(0, 0, {
                'attribute_id': attribute.id,
                'value_ids': [(6, 0, [black.id, white.id])],
            })],
        })
        variant = product.product_variant_ids[:1]
        supplier = self.env['product.supplierinfo'].create({
            'partner_id': vendor.id, 'product_tmpl_id': product.id,
            'product_id': variant.id, 'price': 10000,
        })
        self.assertEqual(supplier.product_id, variant)

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
