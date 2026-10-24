# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    managed_profile = fields.Selection(
        [('core_commerce', 'Core Commerce')],
        required=True,
        default='core_commerce',
    )
    managed_multi_currency = fields.Boolean(string='Multi-currency')
    managed_product_variants = fields.Boolean(string='Product Variants')
    managed_multiple_warehouses = fields.Boolean(string='Multiple Warehouses')
    managed_lots_serials = fields.Boolean(string='Lots and Serial Numbers')

    def _managed_capabilities(self):
        self.ensure_one()
        return {
            'multiCurrency': self.managed_multi_currency,
            'productVariants': self.managed_product_variants,
            'multipleWarehouses': self.managed_multiple_warehouses,
            'lotsSerials': self.managed_lots_serials,
        }
