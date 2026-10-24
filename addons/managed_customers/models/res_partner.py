from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'managed_customers.action_customers':
            return super()._managed_ui_contract(action_xmlid)
        return self._managed_profile_contract('customer')

    @api.model
    def _managed_profile_contract(self, role):
        fields_by_name = self._fields
        names = [name for name in (
            'image_1920', 'company_type', 'name', 'parent_id', 'function', 'email', 'phone', 'mobile', 'website',
            'street', 'street2', 'city', 'state_id', 'zip', 'country_id', 'vat', 'l10n_id_pkp', 'l10n_id_nik',
            'l10n_id_tku', 'l10n_id_buyer_document_type', 'l10n_id_buyer_document_number', 'l10n_id_tax_name',
            'l10n_id_tax_address', 'l10n_id_kode_transaksi', 'user_id', 'property_product_pricelist',
            'property_payment_term_id', 'property_supplier_payment_term_id', 'property_purchase_currency_id',
            'category_id', 'lang', 'comment', 'managed_address_ids', 'is_company', 'active',
        ) if name in fields_by_name]
        return {
            'list': {'title': role.title() + 's', 'fields': [name for name in ('name', 'phone', 'email', 'city', 'country_id', 'vat') if name in fields_by_name], 'default_order': 'display_name asc'},
            'form': {'title': role.title(), 'fields': [{'name': n, **({'widget': 'image'} if n == 'image_1920' else {})} for n in names], 'write_fields': [n for n in names if n not in {'is_company'}], 'buttons': []},
        }
