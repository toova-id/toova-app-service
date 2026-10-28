# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestManagedCore(TransactionCase):

    def test_contract_fallback(self):
        self.assertIsNone(self.env['res.partner']._managed_ui_contract('base.action_partner_form'))
