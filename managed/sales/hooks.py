# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    api.Environment(cr, SUPERUSER_ID, {})['sale.order']._managed_configure_document_sequence()
