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


class ResPartner(models.Model):
    _inherit = 'res.partner'

    managed_email_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_phone_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_vat_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)
    managed_nik_normalized = fields.Char(compute='_compute_managed_identity', store=True, index=True)

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
            return self.browse()
        Partner = self.with_context(active_test=False).sudo()
        company_domain = [('company_id', 'in', [False, self.company_id.id or self.env.company.id])]
        checks = [
            ('managed_vat_normalized', self.managed_vat_normalized, _('NPWP/TIN')),
            ('managed_nik_normalized', self.managed_nik_normalized, _('NIK')),
        ]
        for field_name, value, label in checks:
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
                raise ValidationError(_('%(label)s already belongs to %(partner)s. Use the existing contact instead.', label=label, partner=duplicate.display_name))

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._check_managed_duplicate()
        return partners

    def write(self, vals):
        result = super().write(vals)
        self._check_managed_duplicate()
        return result

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        supported = {
            'contacts.action_contacts', 'base.action_partner_form',
            'account.res_partner_action_customer', 'account.res_partner_action_supplier',
        }
        if action_xmlid not in supported:
            return super()._managed_ui_contract(action_xmlid)

        fields_by_name = self._fields
        def available(*names):
            return [name for name in names if name in fields_by_name]

        list_fields = available('name', 'phone', 'email', 'city', 'country_id', 'vat')
        form_fields = available(
            'image_1920', 'company_type', 'name', 'parent_id', 'function',
            'email', 'phone', 'mobile', 'website',
            'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
            'vat', 'l10n_id_pkp', 'l10n_id_nik', 'l10n_id_tku',
            'l10n_id_buyer_document_type', 'l10n_id_buyer_document_number',
            'l10n_id_tax_name', 'l10n_id_tax_address', 'l10n_id_kode_transaksi',
            'user_id', 'property_product_pricelist', 'property_payment_term_id',
            'property_supplier_payment_term_id', 'property_purchase_currency_id',
            'category_id', 'lang', 'tz', 'comment', 'is_company', 'active',
        )
        write_fields = [name for name in form_fields if name not in {'is_company'}]
        mode = 'supplier' if action_xmlid == 'account.res_partner_action_supplier' else 'customer' if action_xmlid in {'base.action_partner_form', 'account.res_partner_action_customer'} else 'contact'
        filters = []
        if 'customer_rank' in fields_by_name:
            filters.append({'name': 'customers', 'label': 'Customers', 'domain': [('customer_rank', '>', 0)]})
        if 'supplier_rank' in fields_by_name:
            filters.append({'name': 'vendors', 'label': 'Vendors', 'domain': [('supplier_rank', '>', 0)]})
        return {
            'list': {
                'title': {'supplier': 'Vendors', 'customer': 'Customers'}.get(mode, 'Contacts'),
                'fields': list_fields,
                'default_order': 'display_name asc, id desc',
                'filters': filters,
            },
            'form': {
                'title': 'Contact',
                'fields': [
                    {'name': name, **({'widget': 'image'} if name == 'image_1920' else {})}
                    for name in form_fields
                ],
                'write_fields': write_fields,
                'buttons': [],
            },
        }
