# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    general = env['mail.channel'].search([('channel_type', '=', 'channel'), ('name', '=', 'Umum')], limit=1)
    if not general:
        general = env['mail.channel'].create({'name': 'Umum', 'channel_type': 'channel'})
    users = env['res.users'].search([('active', '=', True), ('share', '=', False)])
    general.add_members(users.mapped('partner_id').ids, post_joined_message=False)
    administrator = env['managed.settings.role'].search([('name', '=', 'Tenant Administrator')], limit=1)
    if administrator:
        existing = set(administrator.grant_ids.mapped('permission_key'))
        grants = [(0, 0, {'permission_key': key, 'level': 'write'}) for key in ('inbox.messages', 'inbox.channels', 'inbox.activities') if key not in existing]
        if grants:
            administrator.with_context(managed_settings_bootstrap=True).write({'grant_ids': grants})
    env['ir.ui.menu'].clear_caches()
