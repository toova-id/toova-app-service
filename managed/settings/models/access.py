# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

PERMISSION_LEVELS = [('none', 'Tidak ada'), ('read', 'Read'), ('write', 'Write')]


def _registry(env):
    return env['managed.settings.registry']._managed_registry()

def _permission_labels(env):
    return {key: item['label'] for key, item in _registry(env)['permissions'].items()}

def _permission_groups(env):
    return {
        key: item.get('groups', {})
        for key, item in _registry(env)['permissions'].items()
        if item.get('groups')
    }

def _permission_selection(records):
    return [(key, item['label']) for key, item in _registry(records.env)['permissions'].items()]


class ManagedSettingsRole(models.Model):
    _name = 'managed.settings.role'
    _description = 'Managed Settings Role'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    grant_ids = fields.One2many('managed.settings.role.grant', 'role_id', string='Akses')
    user_ids = fields.Many2many('res.users', 'managed_settings_role_user_rel', 'role_id', 'user_id', string='Pengguna')

    @api.model_create_multi
    def create(self, vals_list):
        roles = super().create(vals_list)
        roles.user_ids._managed_sync_permission_groups()
        roles._check_managed_admin_lockout()
        return roles

    def write(self, vals):
        users = self.user_ids
        result = super().write(vals)
        (users | self.user_ids)._managed_sync_permission_groups()
        self._check_managed_admin_lockout()
        return result

    def unlink(self):
        users = self.user_ids
        result = super().unlink()
        users._managed_sync_permission_groups()
        self.env['managed.settings.role']._check_managed_admin_lockout()
        return result

    @api.model
    def _check_managed_admin_lockout(self):
        if self.env.context.get('managed_settings_bootstrap'):
            return
        users = self.env['res.users'].sudo().with_context(active_test=False).search([('active', '=', True), ('share', '=', False)])
        for key in ('settings.users', 'settings.roles'):
            if not any(user._managed_permission_level(key) == 'write' for user in users):
                raise ValidationError(_('Minimal satu pengguna aktif harus memiliki akses Write untuk %(permission)s.', permission=_permission_labels(self.env)[key]))

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'settings.action_roles':
            return super()._managed_ui_contract(action_xmlid)
        return {
            'list': {
                'title': 'Role & Akses',
                'fields': ['name', 'active', 'user_ids'],
                'default_order': 'name',
                'delete': False,
            },
            'form': {
                'title': 'Role & Akses',
                'fields': [
                    {'name': 'name', 'label': 'Nama role'},
                    {'name': 'active', 'label': 'Aktif'},
                    {'name': 'user_ids', 'label': 'Pengguna'},
                    {'name': 'grant_ids', 'label': 'Hak akses', 'widget': 'managed_permission_matrix', 'relation': {
                        'editable': True,
                        'inverse_field': 'role_id',
                        'columns': [
                            {'name': 'permission_key', 'label': 'Feature / Subfeature', 'selection': _permission_selection(self)},
                            {'name': 'level', 'label': 'Level', 'selection': PERMISSION_LEVELS},
                        ],
                    }},
                ],
                'write_fields': ['name', 'active', 'user_ids', 'grant_ids'],
                'buttons': [],
            },
        }


class ManagedSettingsRoleGrant(models.Model):
    _name = 'managed.settings.role.grant'
    _description = 'Managed Settings Role Grant'
    _order = 'permission_key'

    role_id = fields.Many2one('managed.settings.role', required=True, ondelete='cascade', index=True)
    permission_key = fields.Selection(selection=_permission_selection, required=True, index=True)
    level = fields.Selection(PERMISSION_LEVELS, required=True, default='read')

    _sql_constraints = [
        ('role_permission_unique', 'unique(role_id, permission_key)', 'Permission hanya boleh muncul sekali pada role.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        grants = super().create(vals_list)
        grants.role_id.user_ids._managed_sync_permission_groups()
        grants.role_id._check_managed_admin_lockout()
        return grants

    def write(self, vals):
        roles = self.role_id
        result = super().write(vals)
        roles |= self.role_id
        roles.user_ids._managed_sync_permission_groups()
        roles._check_managed_admin_lockout()
        return result

    def unlink(self):
        roles = self.role_id
        result = super().unlink()
        roles.user_ids._managed_sync_permission_groups()
        roles._check_managed_admin_lockout()
        return result


class ResUsers(models.Model):
    _inherit = 'res.users'

    managed_role_ids = fields.Many2many(
        'managed.settings.role', 'managed_settings_role_user_rel', 'user_id', 'role_id', string='Role managed',
    )

    def _managed_permission_level(self, permission_key):
        self.ensure_one()
        if permission_key not in _registry(self.env)['permissions']:
            return 'none'
        if self.id == self.env.ref('base.user_root').id:
            return 'write'
        levels = self.sudo().managed_role_ids.filtered('active').grant_ids.filtered(
            lambda grant: grant.permission_key == permission_key
        ).mapped('level')
        return 'write' if 'write' in levels else 'read' if 'read' in levels else 'none'

    def _managed_has_permission(self, permission_key, level='read'):
        current = self._managed_permission_level(permission_key)
        return current == 'write' or level == 'read' and current == 'read'

    def _managed_sync_permission_groups(self):
        if not self or self.env.context.get('managed_permission_sync'):
            return
        group_map = _permission_groups(self.env)
        managed_groups = self.env['res.groups'].browse([
            self.env.ref(xmlid).id
            for groups in group_map.values()
            for xmlid in groups.values()
        ])
        for user in self.with_context(active_test=False):
            desired = self.env['res.groups']
            for key, groups in group_map.items():
                level = user._managed_permission_level(key)
                if level != 'none':
                    desired |= self.env.ref(groups[level])
            commands = [(3, group.id) for group in managed_groups - desired]
            commands += [(4, group.id) for group in desired - user.groups_id]
            if commands:
                super(ResUsers, user.with_context(managed_permission_sync=True)).write({'groups_id': commands})

    def write(self, vals):
        result = super().write(vals)
        if 'managed_role_ids' in vals:
            self._managed_sync_permission_groups()
        if {'active', 'managed_role_ids'} & vals.keys() and not self.env.context.get('managed_permission_sync'):
            self.env['managed.settings.role']._check_managed_admin_lockout()
        return result


class ManagedSettingsUser(models.Model):
    _name = 'managed.settings.user'
    _description = 'Managed Settings User'
    _order = 'user_id'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    name = fields.Char(related='user_id.name', readonly=True)
    login = fields.Char(related='user_id.login', readonly=True)
    active = fields.Boolean(related='user_id.active', readonly=True)
    lang = fields.Selection(related='user_id.lang', readonly=True)
    tz = fields.Selection(related='user_id.tz', readonly=True)
    role_ids = fields.Many2many(related='user_id.managed_role_ids', readonly=True)

    _sql_constraints = [('user_unique', 'unique(user_id)', 'Pengguna sudah terdaftar.')]

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for vals in vals_list:
            existing = self.env['res.users'].sudo().browse(vals.get('user_id')).exists()
            if existing:
                user = existing
            else:
                values = {name: vals.get(name) for name in ('name', 'login', 'active', 'lang', 'tz') if name in vals}
                values.update({
                    'company_id': self.env.company.id,
                    'company_ids': [(6, 0, [self.env.company.id])],
                    'share': False,
                })
                user = self.env['res.users'].sudo().create(values)
                if 'role_ids' in vals:
                    user.sudo().write({'managed_role_ids': vals['role_ids']})
            records |= super(ManagedSettingsUser, self).create({'user_id': user.id})
        self.env['managed.settings.role']._check_managed_admin_lockout()
        return records

    def write(self, vals):
        allowed = {name: vals[name] for name in ('name', 'login', 'active', 'lang', 'tz') if name in vals}
        allowed.update({
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
        })
        if 'role_ids' in vals:
            allowed['managed_role_ids'] = vals['role_ids']
        self.user_id.sudo().write(allowed)
        self.env['managed.settings.role']._check_managed_admin_lockout()
        return True

    def unlink(self):
        raise ValidationError(_('Nonaktifkan pengguna, jangan hapus histori pengguna.'))

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'settings.action_users':
            return super()._managed_ui_contract(action_xmlid)
        return {
            'list': {
                'title': 'Pengguna',
                'fields': ['name', 'login', 'active', 'role_ids'],
                'default_order': 'name',
                'delete': False,
            },
            'form': {
                'title': 'Pengguna',
                'fields': [
                    {'name': 'name', 'label': 'Nama'},
                    {'name': 'login', 'label': 'Email / login'},
                    {'name': 'active', 'label': 'Aktif'},
                    {'name': 'lang', 'label': 'Bahasa'},
                    {'name': 'tz', 'label': 'Zona waktu'},
                    {'name': 'role_ids', 'label': 'Role'},
                ],
                'write_fields': ['name', 'login', 'active', 'lang', 'tz', 'role_ids'],
                'buttons': [],
            },
        }


class ManagedSettingsCompany(models.Model):
    _name = 'managed.settings.company'
    _description = 'Managed Settings Company'
    _order = 'name'

    company_id = fields.Many2one('res.company', required=True, ondelete='cascade', index=True)
    logo = fields.Binary(related='company_id.logo', readonly=True)
    name = fields.Char(related='company_id.name', readonly=True)
    street = fields.Char(related='company_id.street', readonly=True)
    street2 = fields.Char(related='company_id.street2', readonly=True)
    city = fields.Char(related='company_id.city', readonly=True)
    state_id = fields.Many2one(related='company_id.state_id', readonly=True)
    zip = fields.Char(related='company_id.zip', readonly=True)
    country_id = fields.Many2one(related='company_id.country_id', readonly=True)
    phone = fields.Char(related='company_id.phone', readonly=True)
    email = fields.Char(related='company_id.email', readonly=True)
    website = fields.Char(related='company_id.website', readonly=True)
    currency_id = fields.Many2one(related='company_id.currency_id', readonly=True)
    vat = fields.Char(related='company_id.vat', readonly=True)

    _sql_constraints = [('company_unique', 'unique(company_id)', 'Profil perusahaan sudah tersedia.')]

    def write(self, vals):
        allowed = {name: vals[name] for name in (
            'logo', 'name', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
            'phone', 'email', 'website', 'vat',
        ) if name in vals}
        self.company_id.sudo().write(allowed)
        return True

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'settings.action_company_profile':
            return super()._managed_ui_contract(action_xmlid)
        fields_list = [
            {'name': 'logo', 'label': 'Logo', 'widget': 'image'},
            {'name': 'name', 'label': 'Nama legal'},
            {'name': 'street', 'label': 'Alamat'},
            {'name': 'street2', 'label': 'Alamat lanjutan'},
            {'name': 'city', 'label': 'Kota'},
            {'name': 'state_id', 'label': 'Provinsi'},
            {'name': 'zip', 'label': 'Kode pos'},
            {'name': 'country_id', 'label': 'Negara'},
            {'name': 'phone', 'label': 'Telepon'},
            {'name': 'email', 'label': 'Email'},
            {'name': 'website', 'label': 'Website'},
            {'name': 'currency_id', 'label': 'Mata uang'},
            {'name': 'vat', 'label': 'NPWP / TIN'},
        ]
        return {
            'list': {
                'title': 'Profil Perusahaan',
                'fields': ['logo', 'name', 'email', 'phone', 'country_id'],
                'default_order': 'name',
                'create': False,
                'delete': False,
            },
            'form': {
                'title': 'Profil Perusahaan',
                'fields': fields_list,
                'write_fields': [field['name'] for field in fields_list if field['name'] != 'currency_id'],
                'create': False,
                'buttons': [],
            },
        }



class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_settings_sections(self):
        return [
            *super()._managed_settings_sections(),
            {'key': 'general', 'placement': 'main', 'label': 'General Information', 'description': 'Identitas legal, kontak, alamat, branding, dan pajak tenant.', 'icon': 'building-2', 'sequence': 10, 'permission': 'settings.company', 'provider': 'managed.settings.general'},
            {'key': 'users', 'placement': 'main', 'label': 'Pengguna', 'description': 'Kelola pengguna internal tenant.', 'icon': 'users', 'sequence': 20, 'permission': 'settings.users', 'action_xmlid': 'settings.action_users'},
            {'key': 'roles', 'placement': 'main', 'label': 'Role & Akses', 'description': 'Akses None, Read, atau Write per subfeature.', 'icon': 'shield-check', 'sequence': 30, 'permission': 'settings.roles', 'action_xmlid': 'settings.action_roles'},
        ]

    @api.model
    def _managed_permission_catalog(self):
        return [
            *super()._managed_permission_catalog(),
            {
                'key': 'settings', 'label': 'Settings', 'sequence': 90,
                'permissions': [
                    {'key': 'settings.company', 'label': 'Profil Perusahaan', 'groups': {'read': 'settings.group_settings_company_read', 'write': 'settings.group_settings_company_write'}},
                    {'key': 'settings.users', 'label': 'Pengguna', 'groups': {'read': 'settings.group_settings_users_read', 'write': 'settings.group_settings_users_write'}},
                    {'key': 'settings.roles', 'label': 'Role & Akses', 'groups': {'read': 'settings.group_settings_roles_read', 'write': 'settings.group_settings_roles_write'}},
                ],
            },
        ]

    @api.model
    def _managed_action_permissions(self):
        return {
            **super()._managed_action_permissions(),
            'settings.action_settings': 'settings.company',
            'settings.action_company_profile': 'settings.company',
            'settings.action_users': 'settings.users',
            'settings.action_roles': 'settings.roles',
        }

    @api.model
    def _managed_menu_permissions(self):
        return {
            **super()._managed_menu_permissions(),
            'settings.menu_company_profile': 'settings.company',
            'settings.menu_users': 'settings.users',
            'settings.menu_roles': 'settings.roles',
        }
