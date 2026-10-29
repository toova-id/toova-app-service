# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'finance.action_customer_invoices':
            return super()._managed_ui_contract(action_xmlid)
        read_only = self.env.user._managed_permission_level('finance.customer_invoices') != 'write'
        fields = [
            {'name': 'name', 'label': 'Nomor'},
            {'name': 'move_type', 'label': 'Jenis dokumen'},
            {'name': 'partner_id', 'label': 'Pelanggan'},
            {'name': 'invoice_date', 'label': 'Tanggal invoice'},
            {'name': 'invoice_date_due', 'label': 'Jatuh tempo'},
            {'name': 'invoice_payment_term_id', 'label': 'Termin pembayaran'},
            {'name': 'invoice_origin', 'label': 'Pesanan sumber'},
            {'name': 'ref', 'label': 'Referensi'},
            {'name': 'currency_id', 'label': 'Mata uang'},
            {'name': 'invoice_line_ids', 'label': 'Baris invoice', 'relation': {
                'editable': False,
                'inverse_field': 'move_id',
                'columns': [
                    {'name': 'product_id', 'label': 'Produk / Variant'},
                    {'name': 'name', 'label': 'Deskripsi'},
                    {'name': 'quantity', 'label': 'Kuantitas'},
                    {'name': 'product_uom_id', 'label': 'Satuan'},
                    {'name': 'price_unit', 'label': 'Harga satuan'},
                    {'name': 'tax_ids', 'label': 'Pajak'},
                    {'name': 'price_subtotal', 'label': 'Subtotal'},
                ],
            }},
            {'name': 'narration', 'label': 'Catatan'},
            {'name': 'amount_untaxed', 'label': 'Subtotal'},
            {'name': 'amount_tax', 'label': 'Pajak'},
            {'name': 'amount_total', 'label': 'Total'},
            {'name': 'amount_residual', 'label': 'Sisa tagihan'},
            {'name': 'payment_state', 'label': 'Status pembayaran', 'selection': [
                ('not_paid', 'Belum dibayar'), ('in_payment', 'Dalam pembayaran'),
                ('paid', 'Lunas'), ('partial', 'Dibayar sebagian'),
                ('reversed', 'Dibalik'), ('invoicing_legacy', 'Legacy'),
            ]},
            {'name': 'state', 'label': 'Status', 'widget': 'statusbar', 'selection': [
                ('draft', 'Draf'), ('posted', 'Diposting'), ('cancel', 'Dibatalkan'),
            ]},
        ]
        return {
            'list': {
                'title': 'Faktur Pelanggan',
                'fields': [
                    {'name': 'name', 'label': 'Nomor'},
                    {'name': 'partner_id', 'label': 'Pelanggan'},
                    {'name': 'invoice_date', 'label': 'Tanggal'},
                    {'name': 'invoice_date_due', 'label': 'Jatuh tempo'},
                    {'name': 'amount_total', 'label': 'Total'},
                    {'name': 'amount_residual', 'label': 'Sisa'},
                    {'name': 'payment_state', 'label': 'Pembayaran', 'widget': 'badge'},
                    {'name': 'state', 'label': 'Status', 'widget': 'badge'},
                ],
                'read_fields': ['currency_id'],
                'default_order': 'invoice_date desc, id desc',
                'create': False,
                'delete': False,
                'filters': [
                    {'name': 'draft', 'label': 'Draf', 'domain': [('state', '=', 'draft')]},
                    {'name': 'unpaid', 'label': 'Belum lunas', 'domain': [('state', '=', 'posted'), ('payment_state', 'in', ('not_paid', 'partial'))]},
                    {'name': 'paid', 'label': 'Lunas', 'domain': [('payment_state', '=', 'paid')]},
                ],
            },
            'form': {
                'title': 'Faktur Pelanggan',
                'fields': fields,
                'write_fields': ['partner_id', 'invoice_date', 'invoice_date_due', 'invoice_payment_term_id', 'ref', 'currency_id', 'narration'],
                'create': False,
                'write': not read_only,
                'status_field': 'state',
                'status_visible': ['draft', 'posted'],
                'buttons': [] if read_only else [
                    {
                        'name': 'action_post', 'label': 'Posting invoice', 'type': 'object', 'primary': True,
                        'modifiers': {'invisible': [('state', '!=', 'draft')]},
                    },
                    {
                        'name': 'action_register_payment', 'label': 'Catat pembayaran', 'type': 'object', 'primary': True,
                        'modifiers': {'invisible': ['|', ('state', '!=', 'posted'), ('payment_state', 'not in', ['not_paid', 'partial'])]},
                    },
                    {
                        'name': 'button_cancel', 'label': 'Batalkan', 'type': 'object',
                        'modifiers': {'invisible': [('state', '!=', 'draft')]},
                    },
                ],
            },
        }


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'finance.action_payments':
            return super()._managed_ui_contract(action_xmlid)
        return {
            'list': {
                'title': 'Pembayaran',
                'fields': [
                    {'name': 'name', 'label': 'Nomor'},
                    {'name': 'date', 'label': 'Tanggal'},
                    {'name': 'partner_id', 'label': 'Pelanggan / Vendor'},
                    {'name': 'journal_id', 'label': 'Jurnal'},
                    {'name': 'payment_type', 'label': 'Arah'},
                    {'name': 'amount', 'label': 'Nominal'},
                    {'name': 'state', 'label': 'Status', 'widget': 'badge'},
                ],
                'read_fields': ['currency_id'],
                'default_order': 'date desc, id desc',
                'create': False,
                'delete': False,
                'filters': [],
            },
            'form': {
                'title': 'Pembayaran',
                'fields': [
                    {'name': 'name', 'label': 'Nomor'},
                    {'name': 'date', 'label': 'Tanggal'},
                    {'name': 'partner_id', 'label': 'Pelanggan / Vendor'},
                    {'name': 'journal_id', 'label': 'Jurnal'},
                    {'name': 'payment_method_line_id', 'label': 'Metode pembayaran'},
                    {'name': 'payment_type', 'label': 'Arah'},
                    {'name': 'partner_type', 'label': 'Tipe mitra'},
                    {'name': 'amount', 'label': 'Nominal'},
                    {'name': 'currency_id', 'label': 'Mata uang'},
                    {'name': 'payment_reference', 'label': 'Referensi'},
                    {'name': 'is_reconciled', 'label': 'Terekonsiliasi'},
                    {'name': 'state', 'label': 'Status', 'widget': 'statusbar'},
                ],
                'write_fields': [],
                'create': False,
                'write': False,
                'status_field': 'state',
                'status_visible': ['draft', 'posted'],
                'buttons': [],
            },
        }


class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_permission_catalog(self):
        return [
            *super()._managed_permission_catalog(),
            {'key': 'finance', 'label': 'Keuangan', 'sequence': 60, 'permissions': [
                {'key': 'finance.customer_invoices', 'label': 'Faktur Pelanggan', 'groups': {
                    'read': 'finance.group_customer_invoices_read',
                    'write': 'finance.group_customer_invoices_write',
                }},
                {'key': 'finance.payments', 'label': 'Pembayaran', 'groups': {
                    'read': 'finance.group_payments_read',
                    'write': 'finance.group_payments_write',
                }},
            ]},
        ]

    @api.model
    def _managed_action_permissions(self):
        return {
            **super()._managed_action_permissions(),
            'finance.action_customer_invoices': 'finance.customer_invoices',
            'finance.action_payments': 'finance.payments',
        }

    @api.model
    def _managed_menu_permissions(self):
        return {
            **super()._managed_menu_permissions(),
            'finance.menu_customer_invoices': 'finance.customer_invoices',
            'finance.menu_payments': 'finance.payments',
        }
