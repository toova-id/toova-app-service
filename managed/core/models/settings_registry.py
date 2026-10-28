# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class ManagedSettingsRegistry(models.AbstractModel):
    _name = 'managed.settings.registry'
    _description = 'Managed Settings Contribution Registry'

    @api.model
    def _managed_settings_sections(self):
        return []

    @api.model
    def _managed_permission_catalog(self):
        return []

    @api.model
    def _managed_action_permissions(self):
        return {}

    @api.model
    def _managed_menu_permissions(self):
        return {}

    @api.model
    def _managed_registry(self):
        sections = self._managed_settings_sections()
        permissions = self._managed_permission_catalog()
        action_permissions = self._managed_action_permissions()
        menu_permissions = self._managed_menu_permissions()
        section_keys = [item.get('key') for item in sections]
        permission_keys = [item.get('key') for feature in permissions for item in feature.get('permissions', [])]
        duplicate_sections = {key for key in section_keys if key and section_keys.count(key) > 1}
        duplicate_permissions = {key for key in permission_keys if key and permission_keys.count(key) > 1}
        if duplicate_sections:
            raise ValidationError(_('Duplicate managed settings section: %(keys)s', keys=', '.join(sorted(duplicate_sections))))
        if duplicate_permissions:
            raise ValidationError(_('Duplicate managed permission: %(keys)s', keys=', '.join(sorted(duplicate_permissions))))
        known = set(permission_keys)
        for section in sections:
            if not section.get('key') or not section.get('label') or not section.get('permission'):
                raise ValidationError(_('Managed settings contribution is incomplete.'))
            if section.get('placement') not in {'main', 'advanced'}:
                raise ValidationError(_('Managed settings placement must be main or advanced.'))
            if section['permission'] not in known:
                raise ValidationError(_('Unknown settings permission: %(key)s', key=section['permission']))
            provider = section.get('provider')
            if provider and provider not in self.env:
                raise ValidationError(_('Unknown settings provider: %(provider)s', provider=provider))
        unknown = (set(action_permissions.values()) | set(menu_permissions.values())) - known
        if unknown:
            raise ValidationError(_('Unknown managed permission mapping: %(keys)s', keys=', '.join(sorted(unknown))))
        return {
            'sections': sorted(sections, key=lambda item: (item.get('sequence', 100), item['key'])),
            'features': permissions,
            'permissions': {item['key']: item for feature in permissions for item in feature.get('permissions', [])},
            'actions': action_permissions,
            'menus': menu_permissions,
        }
