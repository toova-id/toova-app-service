# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    internal = env.ref('base.group_user')
    for xmlid in ('product.group_product_variant', 'product.group_product_pricelist', 'uom.group_uom'):
        internal._apply_group(env.ref(xmlid))
