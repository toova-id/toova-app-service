# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestManagedCore(TransactionCase):

    def test_contract_fallback(self):
        self.assertIsNone(self.env['res.partner']._managed_ui_contract('base.action_partner_form'))

    def test_managed_company_default_forces_current_company(self):
        other = self.env['res.company'].create({'name': 'Other Managed Company'})
        values = self.env['product.pricelist']._managed_apply_company_default({'company_id': other.id, 'name': 'Retail'})
        self.assertEqual(values['company_id'], self.env.company.id)

    def test_managed_company_default_ignores_models_without_company(self):
        values = {'name': 'Managed Category'}
        self.assertEqual(self.env['product.category']._managed_apply_company_default(values), values)

    def test_managed_contract_omits_company_field(self):
        contract = self.env['product.pricelist']._managed_ui_contract('products.action_product_pricelists')
        fields = [item if isinstance(item, str) else item['name'] for item in contract['form']['fields']]
        self.assertNotIn('company_id', fields)
        self.assertNotIn('company_id', contract['form']['write_fields'])
        self.assertEqual(self.env['product.pricelist']._managed_apply_company_default({})['company_id'], self.env.company.id)
