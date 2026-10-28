# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestManagedModuleActivation(TransactionCase):

    def test_managed_catalog_and_people_have_no_sub_feature_flags(self):
        internal = self.env.ref('base.group_user')
        for xmlid in (
            'product.group_product_variant',
            'product.group_product_pricelist',
            'uom.group_uom',
        ):
            self.assertIn(self.env.ref(xmlid), internal.trans_implied_ids)
