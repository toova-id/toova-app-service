# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_permission_catalog(self):
        return [
            *super()._managed_permission_catalog(),
            {'key': 'inbox', 'label': 'Inbox', 'sequence': 15, 'permissions': [
                {'key': 'inbox.messages', 'label': 'Pesan', 'groups': {'read': 'discuss.group_inbox_read', 'write': 'discuss.group_inbox_write'}},
                {'key': 'inbox.channels', 'label': 'Kelola Channel', 'groups': {'read': 'discuss.group_channel_manage_read', 'write': 'discuss.group_channel_manage_write'}},
                {'key': 'inbox.activities', 'label': 'Aktivitas', 'groups': {'read': 'discuss.group_activities_read', 'write': 'discuss.group_activities_write'}},
            ]},
        ]

    @api.model
    def _managed_action_permissions(self):
        return {**super()._managed_action_permissions(), 'mail.action_discuss': 'inbox.messages'}

    @api.model
    def _managed_menu_permissions(self):
        return {**super()._managed_menu_permissions(), 'mail.menu_root_discuss': 'inbox.messages'}
