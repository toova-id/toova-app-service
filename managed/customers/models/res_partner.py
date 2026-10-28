from odoo import api, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'customers.action_customers':
            return super()._managed_ui_contract(action_xmlid)
        return self._managed_profile_contract('customer')

    @api.model
    def _managed_profile_contract(self, role):
        fields_by_name = self._fields
        names = [name for name in (
            'image_1920', 'company_type', 'name', 'parent_id', 'function', 'email', 'phone', 'mobile', 'website',
            'managed_address_text', 'city', 'state_id', 'zip', 'country_id',
            'managed_indonesia_regency_id', 'managed_indonesia_district_id', 'managed_indonesia_village_id',
            'vat', 'l10n_id_pkp', 'l10n_id_nik',
            'l10n_id_tku', 'l10n_id_buyer_document_type', 'l10n_id_buyer_document_number', 'l10n_id_tax_name',
            'l10n_id_tax_address', 'l10n_id_kode_transaksi', 'user_id', 'property_product_pricelist',
            'property_payment_term_id', 'property_supplier_payment_term_id', 'property_purchase_currency_id',
            'property_account_position_id', 'receipt_reminder_email', 'reminder_date_before_receipt', 'bank_ids',
            'category_id', 'lang', 'comment', 'managed_address_ids', 'child_ids', 'is_company', 'active',
        ) if name in fields_by_name]
        fields = []
        for name in names:
            config = {'name': name}
            if name == 'image_1920':
                config['widget'] = 'image'
            elif name == 'managed_address_ids':
                config.update({
                    'widget': 'managed_addresses',
                    'relation': {
                        'editable': True,
                        'inverse_field': 'account_id',
                        'columns': [
                            'label', 'recipient_name', 'recipient_phone', 'recipient_email',
                            'managed_address_text', 'country_id', 'state_id',
                            'indonesia_regency_id', 'indonesia_district_id', 'indonesia_village_id',
                            'city', 'zip', 'use_for_billing', 'use_for_shipping',
                            'is_default_billing', 'is_default_shipping', 'active',
                        ],
                    },
                })
            elif name == 'child_ids':
                config.update({
                    'widget': 'managed_contacts',
                    'relation': {
                        'editable': True,
                        'inverse_field': 'parent_id',
                        'columns': ['name', 'function', 'email', 'phone', 'mobile', 'active'],
                    },
                })
            elif name == 'bank_ids':
                config.update({
                    'widget': 'managed_bank_accounts',
                    'relation': {
                        'editable': True,
                        'inverse_field': 'partner_id',
                        'columns': [
                            'bank_name', 'bank_bic', 'acc_number', 'acc_holder_name',
                            'currency_id', 'allow_out_payment', 'active',
                        ],
                    },
                })
            fields.append(config)
        return {
            'list': {'title': role.title() + 's', 'fields': [name for name in ('name', 'phone', 'email', 'city', 'country_id', 'vat') if name in fields_by_name], 'default_order': 'display_name asc'},
            'form': {'title': role.title(), 'fields': fields, 'write_fields': [n for n in names if n not in {'is_company'}], 'buttons': []},
        }


class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_permission_catalog(self):
        features = super()._managed_permission_catalog()
        contacts = next((feature for feature in features if feature['key'] == 'contacts'), None)
        permission = {'key': 'contacts.customers', 'label': 'Customers', 'groups': {'read': 'settings.group_contacts_customers_read', 'write': 'settings.group_contacts_customers_write'}}
        if contacts:
            contacts = {**contacts, 'permissions': [*contacts['permissions'], permission]}
            return [contacts if feature['key'] == 'contacts' else feature for feature in features]
        return [*features, {'key': 'contacts', 'label': 'Contacts', 'sequence': 10, 'permissions': [permission]}]

    @api.model
    def _managed_action_permissions(self):
        return {**super()._managed_action_permissions(), 'customers.action_customers': 'contacts.customers'}

    @api.model
    def _managed_menu_permissions(self):
        return {**super()._managed_menu_permissions(), 'customers.menu_customers_root': 'contacts.customers'}
