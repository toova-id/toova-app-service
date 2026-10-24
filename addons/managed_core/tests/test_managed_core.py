# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestManagedCore(TransactionCase):

    def test_default_profile_and_contract(self):
        company = self.env.company
        self.assertEqual(company.managed_profile, 'core_commerce')
        self.assertEqual(company._managed_capabilities()['multiCurrency'], False)
        self.assertIsNone(self.env['res.partner']._managed_ui_contract('base.action_partner_form'))
