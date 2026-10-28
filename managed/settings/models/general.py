# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class ManagedSettingsGeneral(models.AbstractModel):
    _name = 'managed.settings.general'
    _description = 'Managed General Information Settings'

    _allowed_fields = {
        'logo', 'name', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
        'phone', 'email', 'website', 'vat', 'l10n_id_tax_name', 'l10n_id_tax_address',
        'l10n_id_tku', 'l10n_id_pkp',
    }

    @api.model
    def get_values(self):
        company = self.env.company
        partner = company.partner_id
        return {
            'logo': company.logo or False,
            'name': company.name,
            'street': company.street or False,
            'street2': company.street2 or False,
            'city': company.city or False,
            'state_id': company.state_id and [company.state_id.id, company.state_id.name] or False,
            'zip': company.zip or False,
            'country_id': company.country_id and [company.country_id.id, company.country_id.name] or False,
            'phone': company.phone or False,
            'email': company.email or False,
            'website': company.website or False,
            'currency_id': [company.currency_id.id, company.currency_id.name],
            'vat': company.vat or False,
            'l10n_id_tax_name': getattr(company, 'l10n_id_tax_name', False) or False,
            'l10n_id_tax_address': getattr(company, 'l10n_id_tax_address', False) or False,
            'l10n_id_tku': getattr(partner, 'l10n_id_tku', False) or False,
            'l10n_id_pkp': getattr(partner, 'l10n_id_pkp', False),
        }

    @api.model
    def save_values(self, values):
        unknown = set(values) - self._allowed_fields
        if unknown:
            raise ValidationError(_('Field General Information tidak diizinkan: %(fields)s', fields=', '.join(sorted(unknown))))
        company_values = {}
        partner_values = {}
        for name, value in values.items():
            if isinstance(value, (list, tuple)) and name in {'state_id', 'country_id'}:
                value = value[0] if value else False
            if name in {'l10n_id_tku', 'l10n_id_pkp'}:
                partner_values[name] = value
            elif name in self.env.company._fields:
                company_values[name] = value
        if company_values:
            self.env.company.sudo().write(company_values)
        if partner_values:
            self.env.company.partner_id.sudo().write(partner_values)
        return self.get_values()

    @api.model
    def get_readiness(self):
        values = self.get_values()
        missing = [label for key, label in (
            ('name', 'nama legal'), ('country_id', 'negara'), ('email', 'email'), ('phone', 'telepon'), ('vat', 'NPWP/TIN'),
        ) if not values.get(key)]
        return {
            'status': 'warning' if missing else 'ready',
            'message': f"Lengkapi {', '.join(missing[:3])}" if missing else None,
        }
