# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid not in {
            'sale.action_orders',
            'sale.action_quotations',
            'sale.action_quotations_with_onboarding',
            'sale.action_orders_to_invoice',
            'sale.action_orders_upselling',
        }:
            return None

        quotations = action_xmlid in {
            'sale.action_quotations',
            'sale.action_quotations_with_onboarding',
        }
        list_fields = [
            'name', 'create_date' if quotations else 'date_order', 'partner_id',
            {'name': 'user_id', 'widget': 'many2one_avatar_user'}, 'team_id',
            'amount_total', 'invoice_status',
            {'name': 'state', 'widget': 'badge'},
        ]
        locked = {'readonly': [('state', 'in', ['done', 'cancel'])]}
        confirmed = {'readonly': [('state', 'in', ['sale', 'done', 'cancel'])]}
        form_fields = [
            {'name': 'name', 'modifiers': confirmed},
            {'name': 'partner_id', 'modifiers': confirmed},
            {'name': 'partner_invoice_id', 'modifiers': locked},
            {'name': 'partner_shipping_id', 'modifiers': locked},
            {'name': 'date_order', 'modifiers': confirmed},
            {
                'name': 'validity_date',
                'modifiers': {
                    'readonly': confirmed['readonly'],
                    'invisible': [('state', 'in', ['sale', 'done'])],
                },
            },
            {'name': 'commitment_date', 'modifiers': locked},
            'client_order_ref',
            {'name': 'user_id', 'widget': 'many2one_avatar_user'}, 'team_id', 'company_id',
            {'name': 'pricelist_id', 'modifiers': confirmed},
            'payment_term_id', 'fiscal_position_id',
            {
                'name': 'order_line',
                'modifiers': locked,
                'relation': {
                    'editable': True,
                    'inverse_field': 'order_id',
                    'columns': [
                        {'name': 'product_id', 'widget': 'sol_product_many2one'},
                        'name', 'product_uom_qty', 'product_uom', 'price_unit',
                        {'name': 'discount', 'widget': 'percentage'},
                        {'name': 'tax_id', 'widget': 'many2many_tags'},
                        'price_subtotal', 'currency_id', 'display_type',
                    ],
                },
            },
            'note', 'amount_untaxed', 'amount_tax', 'amount_total', 'currency_id',
            'invoice_status', {'name': 'state', 'widget': 'statusbar'},
        ]
        return {
            'list': {
                'title': 'Quotations' if quotations else 'Sales Orders',
                'fields': list_fields,
                'read_fields': ['currency_id'],
                'default_order': 'date_order desc, id desc',
                'filters': [
                    {'name': 'my_orders', 'label': 'My Orders', 'domain': [('user_id', '=', self.env.uid)]},
                    {'name': 'draft', 'label': 'Quotations', 'domain': [('state', 'in', ('draft', 'sent'))]},
                    {'name': 'sales', 'label': 'Sales Orders', 'domain': [('state', 'in', ('sale', 'done'))]},
                    {'name': 'to_invoice', 'label': 'To Invoice', 'domain': [('invoice_status', '=', 'to invoice')]},
                ],
            },
            'form': {
                'title': 'Quotation / Sales Order',
                'fields': form_fields,
                'write_fields': [
                    'name', 'partner_id', 'partner_invoice_id', 'partner_shipping_id',
                    'date_order', 'validity_date', 'commitment_date', 'client_order_ref',
                    'user_id', 'team_id', 'company_id', 'pricelist_id',
                    'payment_term_id', 'fiscal_position_id', 'order_line', 'note',
                ],
                'status_field': 'state',
                'status_visible': ['draft', 'sent', 'sale'],
                'buttons': [
                    {
                        'name': 'action_quotation_send', 'label': 'Send by Email',
                        'type': 'object', 'primary': True,
                        'modifiers': {'invisible': [('state', 'not in', ['draft', 'sent', 'sale'])]},
                    },
                    {
                        'name': 'action_confirm', 'label': 'Confirm',
                        'type': 'object', 'primary': True,
                        'modifiers': {'invisible': [('state', 'not in', ['draft', 'sent'])]},
                    },
                    {
                        'name': 'action_cancel', 'label': 'Cancel', 'type': 'object',
                        'modifiers': {'invisible': [('state', 'not in', ['draft', 'sent', 'sale'])]},
                    },
                    {
                        'name': 'action_draft', 'label': 'Set to Quotation', 'type': 'object',
                        'modifiers': {'invisible': [('state', '!=', 'cancel')]},
                    },
                ],
            },
        }
