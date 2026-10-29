# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    roles = env['managed.settings.role'].sudo().search([('name', '=', 'Tenant Administrator')])
    permission = 'inventory.deliveries'
    for role in roles:
        grant = role.grant_ids.filtered(lambda item: item.permission_key == permission)
        if grant:
            grant.with_context(managed_settings_bootstrap=True).write({'level': 'write'})
        else:
            env['managed.settings.role.grant'].with_context(managed_settings_bootstrap=True).create({
                'role_id': role.id, 'permission_key': permission, 'level': 'write',
            })
    roles.user_ids._managed_sync_permission_groups()
    env['ir.ui.menu'].clear_caches()
