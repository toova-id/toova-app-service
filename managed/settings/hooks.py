# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api



def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    permissions = env['managed.settings.registry']._managed_registry()['permissions']
    administrator = env['managed.settings.role'].with_context(managed_settings_bootstrap=True).create({
        'name': 'Tenant Administrator',
        'grant_ids': [(0, 0, {'permission_key': key, 'level': 'write'}) for key in permissions],
    })
    users = env.ref('base.user_admin') | env.ref('base.user_root')
    administrator.with_context(managed_settings_bootstrap=True).write({'user_ids': [(6, 0, users.ids)]})
    for user in users:
        env['managed.settings.user'].with_context(managed_settings_bootstrap=True).create({'user_id': user.id})
    env['managed.settings.company'].create({'company_id': env.company.id})
    users._managed_sync_permission_groups()
    env['ir.ui.menu'].clear_caches()
