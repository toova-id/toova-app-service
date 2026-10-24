# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


def _compact(value):
    return re.sub(r'[^0-9A-Z]+', '', (value or '').strip().upper()) or False


def _phone(value):
    digits = re.sub(r'\D+', '', value or '')
    if digits.startswith('0'):
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
    _order = 'is_primary desc, label, id'

    account_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    address_partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    label = fields.Char(required=True)
    recipient_name = fields.Char()
    recipient_phone = fields.Char()
    use_for_billing = fields.Boolean()
    use_for_shipping = fields.Boolean()
    use_for_receiving = fields.Boolean()
    is_primary = fields.Boolean()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('account_address_unique', 'unique(account_id, address_partner_id)', 'Address is already attached to this account.'),
    ]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    managed_email_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_phone_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_vat_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_nik_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_role_ids = fields.One2many('managed.partner.role', 'partner_id')
    managed_address_ids = fields.One2many('managed.partner.address', 'account_id')

    @api.depends('email', 'phone', 'mobile', 'vat', 'l10n_id_nik')
    def _compute_managed_identity(self):
        has_nik = 'l10n_id_nik' in self._fields
        for partner in self:
            partner.managed_email_normalized = (partner.email or '').strip().lower() or False
            partner.managed_phone_normalized = _phone(partner.mobile or partner.phone)
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

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._check_managed_duplicate()
        role = self.env.context.get('managed_party_role')
        if role:
            partners._ensure_managed_role(role)
        return partners

    def write(self, vals):
        result = super().write(vals)
        self._check_managed_duplicate()
        role = self.env.context.get('managed_party_role')
        if role:
            self._ensure_managed_role(role)
        return result
