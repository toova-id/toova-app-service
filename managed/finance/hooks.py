# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['account.move']._managed_configure_document_sequences()
    roles = env['managed.settings.role'].sudo().search([('name', '=', 'Tenant Administrator')])
    permissions = ('finance.customer_invoices', 'finance.payments')
    for role in roles:
        for permission in permissions:
            grant = role.grant_ids.filtered(lambda item: item.permission_key == permission)
            if grant:
                grant.with_context(managed_settings_bootstrap=True).write({'level': 'write'})
            else:
                env['managed.settings.role.grant'].with_context(managed_settings_bootstrap=True).create({
                    'role_id': role.id, 'permission_key': permission, 'level': 'write',
                })
    roles.user_ids._managed_sync_permission_groups()
    env['ir.ui.menu'].clear_caches()
