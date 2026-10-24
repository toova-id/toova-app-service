# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


def _compact(value):
    return re.sub(r'[^0-9A-Z]+', '', (value or '').strip().upper()) or False


def _phone(value, country_code=None):
    digits = re.sub(r'\D+', '', value or '')
    if country_code == 'ID' and digits.startswith('0'):
        digits = '62' + digits[1:]
    return digits or False


class ManagedPartnerRole(models.Model):
    _name = 'managed.partner.role'
    _description = 'Managed Partner Role'
    _order = 'partner_id, role'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True)
    role = fields.Selection([
        ('customer', 'Customer'),
        ('vendor', 'Vendor'),
        ('contact', 'Contact Person'),
    ], required=True, index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('partner_role_company_unique', 'unique(partner_id, company_id, role)', 'This role already exists for the party.'),
    ]


class ManagedPartnerAddress(models.Model):
    _name = 'managed.partner.address'
    _description = 'Managed Partner Address'
    _order = 'is_default_shipping desc, is_default_billing desc, label, id'

    account_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    address_partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', index=True)
    label = fields.Char(required=True)
    recipient_name = fields.Char(related='address_partner_id.name', readonly=False, required=True)
    recipient_phone = fields.Char(related='address_partner_id.phone', readonly=False)
    recipient_email = fields.Char(related='address_partner_id.email', readonly=False)
    managed_address_text = fields.Text(related='address_partner_id.managed_address_text', readonly=False, string='Full Address')
    city = fields.Char(related='address_partner_id.city', readonly=False)
    state_id = fields.Many2one(related='address_partner_id.state_id', readonly=False)
    zip = fields.Char(related='address_partner_id.zip', readonly=False)
    country_id = fields.Many2one(related='address_partner_id.country_id', readonly=False)
    indonesia_regency_id = fields.Many2one(
        'managed.indonesia.region', string='Regency/City', ondelete='restrict',
        domain="[('level', '=', 'regency'), ('state_id', '=', state_id)]",
    )
    indonesia_district_id = fields.Many2one(
        'managed.indonesia.region', string='District', ondelete='restrict',
        domain="[('level', '=', 'district'), ('parent_id', '=', indonesia_regency_id)]",
    )
    indonesia_village_id = fields.Many2one(
        'managed.indonesia.region', string='Village', ondelete='restrict',
        domain="[('level', '=', 'village'), ('parent_id', '=', indonesia_district_id)]",
    )
    use_for_billing = fields.Boolean(string='Billing')
    use_for_shipping = fields.Boolean(string='Shipping')
    is_default_billing = fields.Boolean(string='Default Billing')
    is_default_shipping = fields.Boolean(string='Default Shipping')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('account_address_unique', 'unique(account_id, address_partner_id)', 'Address is already attached to this account.'),
    ]

    def _auto_init(self):
        result = super()._auto_init()
        for field_name in ('is_default_billing', 'is_default_shipping'):
            self._cr.execute(f'''UPDATE {self._table} target SET {field_name} = FALSE
                FROM (SELECT id, row_number() OVER (
                    PARTITION BY account_id ORDER BY write_date DESC NULLS LAST, id DESC
                ) position FROM {self._table} WHERE {field_name} IS TRUE AND active IS TRUE) duplicate
                WHERE target.id = duplicate.id AND duplicate.position > 1''')
            self._cr.execute(f'''CREATE UNIQUE INDEX IF NOT EXISTS
                managed_partner_address_one_{field_name}
                ON {self._table} (account_id) WHERE {field_name} IS TRUE AND active IS TRUE''')
        return result

    def _clear_previous_defaults(self, vals):
        account_id = vals.get('account_id') or (self[:1].account_id.id if self else False)
        if not account_id:
            return
        for field_name in ('is_default_billing', 'is_default_shipping'):
            if vals.get(field_name):
                self.search([
                    ('account_id', '=', account_id), (field_name, '=', True),
                    ('id', 'not in', self.ids),
                ]).with_context(managed_default_sync=True).write({field_name: False})

    @api.model_create_multi
    def create(self, vals_list):
        latest_defaults = {}
        for position, vals in enumerate(vals_list):
            for field_name in ('is_default_billing', 'is_default_shipping'):
                if vals.get(field_name):
                    previous = latest_defaults.get((vals.get('account_id'), field_name))
                    if previous is not None:
                        vals_list[previous][field_name] = False
                    latest_defaults[(vals.get('account_id'), field_name)] = position
        for vals in vals_list:
            self._clear_previous_defaults(vals)
            account = self.env['res.partner'].browse(vals.get('account_id')).exists()
            address = self.env['res.partner'].browse(vals.get('address_partner_id')).exists()
            if not address:
                address = self.env['res.partner'].create({
                    'name': vals.get('recipient_name') or vals.get('label'),
                    'parent_id': account.id,
                    'company_id': account.company_id.id,
                    'type': self._address_type(vals),
                })
                vals['address_partner_id'] = address.id
        records = super().create(vals_list)
        records._apply_default_address()
        records._check_managed_address()
        records._sync_address_partner()
        return records

    def write(self, vals):
        self._clear_previous_defaults(vals)
        result = super().write(vals)
        if not self.env.context.get('managed_default_sync'):
            self._apply_default_address()
        self._check_managed_address()
        self._sync_address_partner()
        return result

    def _apply_default_address(self):
        for address in self:
            for field_name in ('is_default_billing', 'is_default_shipping'):
                if address[field_name]:
                    self.search([
                        ('account_id', '=', address.account_id.id),
                        (field_name, '=', True),
                        ('id', '!=', address.id),
                    ]).with_context(managed_default_sync=True).write({field_name: False})

    @api.model
    def _address_type(self, vals):
        if vals.get('use_for_shipping'):
            return 'delivery'
        if vals.get('use_for_billing'):
            return 'invoice'
        return 'other'

    def _check_managed_address(self):
        for address in self:
            if address.address_partner_id == address.account_id or address.address_partner_id.parent_id != address.account_id:
                raise ValidationError(_('Address must belong to this customer.'))
            if address.is_default_billing and not address.use_for_billing:
                raise ValidationError(_('Default billing address must be enabled for billing.'))
            if address.is_default_shipping and not address.use_for_shipping:
                raise ValidationError(_('Default shipping address must be enabled for shipping.'))
            if address.is_default_billing:
                other = self.search([('account_id', '=', address.account_id.id), ('is_default_billing', '=', True), ('id', '!=', address.id)], limit=1)
                if other:
                    raise ValidationError(_('Only one default billing address is allowed.'))
            if address.is_default_shipping:
                other = self.search([('account_id', '=', address.account_id.id), ('is_default_shipping', '=', True), ('id', '!=', address.id)], limit=1)
                if other:
                    raise ValidationError(_('Only one default shipping address is allowed.'))

    @api.onchange('country_id')
    def _onchange_country(self):
        if self.country_id.code != 'ID':
            self.indonesia_regency_id = False
            self.indonesia_district_id = False
            self.indonesia_village_id = False

    @api.onchange('indonesia_regency_id')
    def _onchange_indonesia_regency(self):
        self.indonesia_district_id = False
        self.indonesia_village_id = False
        if self.indonesia_regency_id:
            self.city = self.indonesia_regency_id.name
            self.state_id = self.indonesia_regency_id.state_id

    @api.onchange('indonesia_district_id')
    def _onchange_indonesia_district(self):
        self.indonesia_village_id = False

    @api.onchange('indonesia_village_id')
    def _onchange_indonesia_village(self):
        if self.indonesia_village_id:
            regency = self.indonesia_village_id.parent_id.parent_id
            self.zip = self.indonesia_village_id.postal_code
            self.city = regency.name
            self.state_id = regency.state_id

    def _sync_address_partner(self):
        for address in self:
            vals = {
                'parent_id': address.account_id.id,
                'company_id': address.account_id.company_id.id,
                'type': address._address_type({
                    'use_for_billing': address.use_for_billing,
                    'use_for_shipping': address.use_for_shipping,
                }),
                'active': address.active,
            }
            if address.country_id.code == 'ID':
                vals.update({
                    'city': address.indonesia_regency_id.name or address.city,
                    'state_id': address.indonesia_regency_id.state_id.id or address.state_id.id,
                    'zip': address.indonesia_village_id.postal_code or address.zip,
                })
            address.address_partner_id.with_context(managed_address_sync=True).write(vals)

    def unlink(self):
        raise ValidationError(_('Archive customer addresses instead of deleting them.'))


class ResPartner(models.Model):
    _inherit = 'res.partner'

    managed_email_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_phone_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_vat_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_nik_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_role_ids = fields.One2many('managed.partner.role', 'partner_id')
    managed_address_ids = fields.One2many('managed.partner.address', 'account_id')
    managed_address_text = fields.Text(compute='_compute_managed_address_text', inverse='_inverse_managed_address_text', string='Full Address')
    managed_indonesia_regency_id = fields.Many2one(
        'managed.indonesia.region', string='Regency/City', ondelete='restrict',
        domain="[('level', '=', 'regency'), ('state_id', '=', state_id)]",
    )
    managed_indonesia_district_id = fields.Many2one(
        'managed.indonesia.region', string='District', ondelete='restrict',
        domain="[('level', '=', 'district'), ('parent_id', '=', managed_indonesia_regency_id)]",
    )
    managed_indonesia_village_id = fields.Many2one(
        'managed.indonesia.region', string='Village', ondelete='restrict',
        domain="[('level', '=', 'village'), ('parent_id', '=', managed_indonesia_district_id)]",
    )

    @api.depends('street', 'street2')
    def _compute_managed_address_text(self):
        for partner in self:
            partner.managed_address_text = '\n'.join(filter(None, (partner.street, partner.street2)))

    def _inverse_managed_address_text(self):
        for partner in self:
            lines = [line.strip() for line in (partner.managed_address_text or '').splitlines() if line.strip()]
            partner.street = lines[0] if lines else False
            partner.street2 = '\n'.join(lines[1:]) or False

    @api.onchange('country_id')
    def _onchange_managed_country(self):
        if self.country_id.code != 'ID':
            self.managed_indonesia_regency_id = False
            self.managed_indonesia_district_id = False
            self.managed_indonesia_village_id = False

    @api.onchange('managed_indonesia_regency_id')
    def _onchange_managed_regency(self):
        self.managed_indonesia_district_id = False
        self.managed_indonesia_village_id = False
        if self.managed_indonesia_regency_id:
            self.city = self.managed_indonesia_regency_id.name
            self.state_id = self.managed_indonesia_regency_id.state_id

    @api.onchange('managed_indonesia_district_id')
    def _onchange_managed_district(self):
        self.managed_indonesia_village_id = False

    @api.onchange('managed_indonesia_village_id')
    def _onchange_managed_village(self):
        if self.managed_indonesia_village_id:
            regency = self.managed_indonesia_village_id.parent_id.parent_id
            self.zip = self.managed_indonesia_village_id.postal_code
            self.city = regency.name
            self.state_id = regency.state_id

    @api.depends('email', 'phone', 'mobile', 'vat', 'l10n_id_nik', 'country_id.code')
    def _compute_managed_identity(self):
        has_nik = 'l10n_id_nik' in self._fields
        for partner in self:
            partner.managed_email_normalized = (partner.email or '').strip().lower() or False
            partner.managed_phone_normalized = _phone(partner.mobile or partner.phone, partner.country_id.code)
            partner.managed_vat_normalized = _compact(partner.vat)
            partner.managed_nik_normalized = _compact(partner.l10n_id_nik) if has_nik else False

    def _managed_duplicate(self):
        self.ensure_one()
        if self.parent_id:
            return self.browse(), False
        Partner = self.with_context(active_test=False).sudo()
        company_domain = [('company_id', 'in', [False, self.company_id.id or self.env.company.id])]
        for field_name, value, label in [
            ('managed_vat_normalized', self.managed_vat_normalized, _('NPWP/TIN')),
            ('managed_nik_normalized', self.managed_nik_normalized, _('NIK')),
        ]:
            if value:
                duplicate = Partner.search(company_domain + [(field_name, '=', value), ('id', '!=', self.id)], limit=1)
                if duplicate:
                    return duplicate, label
        return self.browse(), False

    def _managed_default_address(self, address_type):
        default_field = 'is_default_billing' if address_type == 'invoice' else 'is_default_shipping'
        usage_field = 'use_for_billing' if address_type == 'invoice' else 'use_for_shipping'
        return self.managed_address_ids.filtered(
            lambda address: address.active and address[usage_field] and address[default_field]
        )[:1].address_partner_id

    def address_get(self, adr_pref=None):
        result = super().address_get(adr_pref)
        requested = set(adr_pref or [])
        for address_type in requested & {'invoice', 'delivery'}:
            default = self._managed_default_address(address_type)
            if default:
                result[address_type] = default.id
        return result

    def _check_managed_duplicate(self):
        if not self.env.context.get('managed_ui'):
            return
        for partner in self:
            duplicate, label = partner._managed_duplicate()
            if duplicate:
                raise ValidationError(_('%(label)s already belongs to %(partner)s. Use the existing party instead.', label=label, partner=duplicate.display_name))

    @api.model
    def _managed_role_domain(self, role):
        return [('managed_role_ids.role', '=', role), ('managed_role_ids.company_id', '=', self.env.company.id)]

    def _ensure_managed_role(self, role):
        for partner in self:
            self.env['managed.partner.role'].search([
                ('partner_id', '=', partner.id), ('company_id', '=', self.env.company.id), ('role', '=', role),
            ], limit=1) or self.env['managed.partner.role'].create({
                'partner_id': partner.id, 'company_id': self.env.company.id, 'role': role,
            })
            rank = 'customer_rank' if role == 'customer' else 'supplier_rank' if role == 'vendor' else None
            if rank and rank in partner._fields and partner[rank] < 1:
                partner.with_context(managed_ui=False).write({rank: 1})
        return self

    def _ensure_managed_context_role(self):
        role = self.env.context.get('managed_party_role')
        if not role:
            return
        self.filtered(lambda partner: not partner.parent_id)._ensure_managed_role(role)
        self.filtered(lambda partner: partner.parent_id and partner.type == 'contact')._ensure_managed_role('contact')

    @api.model
    def _prepare_managed_address_vals(self, vals):
        vals = dict(vals)
        if 'managed_address_text' in vals:
            lines = [line.strip() for line in (vals.pop('managed_address_text') or '').splitlines() if line.strip()]
            vals['street'] = lines[0] if lines else False
            vals['street2'] = '\n'.join(lines[1:]) or False
        village_id = vals.get('managed_indonesia_village_id')
        regency_id = vals.get('managed_indonesia_regency_id')
        if village_id:
            village = self.env['managed.indonesia.region'].browse(village_id)
            regency = village.parent_id.parent_id
            vals.update({'city': regency.name, 'state_id': regency.state_id.id, 'zip': village.postal_code})
        elif regency_id:
            regency = self.env['managed.indonesia.region'].browse(regency_id)
            vals.update({'city': regency.name, 'state_id': regency.state_id.id})
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create([self._prepare_managed_address_vals(vals) for vals in vals_list])
        partners._check_managed_duplicate()
        partners._ensure_managed_context_role()
        return partners

    def write(self, vals):
        result = super().write(self._prepare_managed_address_vals(vals))
        self._check_managed_duplicate()
        self._ensure_managed_context_role()
        return result
