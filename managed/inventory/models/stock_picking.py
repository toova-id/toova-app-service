# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    managed_demand_qty = fields.Float(related='move_id.product_uom_qty', string='Permintaan', readonly=True)


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    def _managed_document_code(self):
        self.ensure_one()
        if self.sequence_code == 'RET':
            return 'RTN'
        return {'outgoing': 'DO', 'incoming': 'GR', 'internal': 'ST'}[self.code]

    def _managed_assign_document_sequences(self):
        sequences = self.env['ir.sequence'].sudo()
        for picking_type in self.sudo().filtered('sequence_id'):
            code = picking_type._managed_document_code()
            sequence_code = f'managed.stock.{code}.{picking_type.company_id.id}'
            sequence = sequences.search([('code', '=', sequence_code), ('company_id', '=', picking_type.company_id.id)], limit=1)
            values = {
                'name': f'Managed Stock {code}',
                'code': sequence_code,
                'prefix': f'{code}%(y)s%(month)s',
                'padding': 6,
                'use_date_range': True,
                'managed_monthly_reset': True,
                'company_id': picking_type.company_id.id,
            }
            if sequence:
                sequence.write(values)
            else:
                sequence = sequences.create(values)
            picking_type.sequence_id = sequence
        return self

    @api.model
    def _managed_configure_document_sequences(self):
        purchase_sequence = self.env.ref('purchase.seq_purchase_order', raise_if_not_found=False)
        if purchase_sequence:
            purchase_sequence.sudo().write({
                'name': 'Purchase Order',
                'prefix': 'PO%(y)s%(month)s',
                'padding': 6,
                'use_date_range': True,
                'managed_monthly_reset': True,
            })
        picking_types = self.sudo().with_context(active_test=False).search([('sequence_id', '!=', False)])
        return picking_types._managed_assign_document_sequences()

    @api.model_create_multi
    def create(self, vals_list):
        picking_types = super().create(vals_list)
        picking_types._managed_assign_document_sequences()
        return picking_types


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    managed_move_line_ids = fields.One2many('stock.move.line', 'picking_id', string='Managed Operations')

    @api.model
    def _managed_ui_contract(self, action_xmlid):
        if action_xmlid != 'inventory.action_deliveries':
            return super()._managed_ui_contract(action_xmlid)
        read_only = self.env.user._managed_permission_level('inventory.deliveries') != 'write'
        return {
            'list': {
                'title': 'Pengiriman',
                'fields': [
                    {'name': 'name', 'label': 'Nomor'},
                    {'name': 'origin', 'label': 'Pesanan'},
                    {'name': 'partner_id', 'label': 'Pelanggan'},
                    {'name': 'scheduled_date', 'label': 'Jadwal'},
                    {'name': 'products_availability', 'label': 'Ketersediaan'},
                    {'name': 'state', 'label': 'Status', 'widget': 'badge'},
                ],
                'default_order': 'scheduled_date desc, id desc',
                'create': False,
                'delete': False,
                'filters': [
                    {'name': 'ready', 'label': 'Siap dikirim', 'domain': [('state', '=', 'assigned')]},
                    {'name': 'waiting', 'label': 'Menunggu stok', 'domain': [('state', 'in', ('waiting', 'confirmed'))]},
                    {'name': 'done', 'label': 'Selesai', 'domain': [('state', '=', 'done')]},
                ],
            },
            'form': {
                'title': 'Pengiriman',
                'fields': [
                    {'name': 'name', 'label': 'Nomor'},
                    {'name': 'origin', 'label': 'Pesanan'},
                    {'name': 'partner_id', 'label': 'Alamat pengiriman'},
                    {'name': 'scheduled_date', 'label': 'Jadwal'},
                    {'name': 'date_deadline', 'label': 'Batas waktu'},
                    {'name': 'date_done', 'label': 'Tanggal selesai'},
                    {'name': 'picking_type_id', 'label': 'Tipe operasi'},
                    {'name': 'location_id', 'label': 'Dari lokasi'},
                    {'name': 'location_dest_id', 'label': 'Ke lokasi'},
                    {'name': 'products_availability', 'label': 'Ketersediaan'},
                    {'name': 'managed_move_line_ids', 'label': 'Operasi pengiriman', 'widget': 'managed_stock_move_lines', 'relation': {
                        'editable': True,
                        'inverse_field': 'picking_id',
                        'columns': [
                            {'name': 'product_id', 'label': 'Produk / Variant'},
                            {'name': 'managed_demand_qty', 'label': 'Permintaan'},
                            {'name': 'reserved_uom_qty', 'label': 'Direservasi'},
                            {'name': 'qty_done', 'label': 'Selesai'},
                            {'name': 'product_uom_id', 'label': 'Satuan'},
                            {'name': 'lot_id', 'label': 'Lot / Serial', 'widget': 'managed_stock_lot_many2one'},
                            {'name': 'lot_name', 'label': 'Lot / Serial baru'},
                            {'name': 'tracking', 'label': 'Tracking'},
                        ],
                    }},
                    {'name': 'move_ids_without_package', 'label': 'Permintaan', 'relation': {
                        'editable': False,
                        'inverse_field': 'picking_id',
                        'columns': [
                            {'name': 'product_id', 'label': 'Produk / Variant'},
                            {'name': 'product_uom_qty', 'label': 'Permintaan'},
                            {'name': 'reserved_availability', 'label': 'Direservasi'},
                            {'name': 'quantity_done', 'label': 'Selesai'},
                            {'name': 'product_uom', 'label': 'Satuan'},
                        ],
                    }},
                    {'name': 'note', 'label': 'Catatan'},
                    {'name': 'state', 'label': 'Status', 'widget': 'statusbar', 'selection': [
                        ('draft', 'Draf'), ('waiting', 'Menunggu'), ('confirmed', 'Siap diproses'),
                        ('assigned', 'Siap dikirim'), ('done', 'Selesai'), ('cancel', 'Dibatalkan'),
                    ]},
                ],
                'write_fields': ['scheduled_date', 'date_deadline', 'managed_move_line_ids', 'note'],
                'create': False,
                'write': not read_only,
                'status_field': 'state',
                'status_visible': ['draft', 'confirmed', 'assigned', 'done'],
                'buttons': [] if read_only else [
                    {
                        'name': 'action_assign', 'label': 'Cek ketersediaan', 'type': 'object', 'primary': True,
                        'modifiers': {'invisible': [('state', 'not in', ['waiting', 'confirmed', 'assigned'])]},
                    },
                    {
                        'name': 'button_validate', 'label': 'Validasi pengiriman', 'type': 'object', 'primary': True,
                        'modifiers': {'invisible': [('state', 'in', ['draft', 'done', 'cancel'])]},
                    },
                    {
                        'name': 'action_cancel', 'label': 'Batalkan', 'type': 'object',
                        'modifiers': {'invisible': [('state', 'not in', ['draft', 'waiting', 'confirmed', 'assigned'])]},
                    },
                ],
            },
        }

    def _check_managed_delivery(self):
        if not self.env.context.get('managed_ui'):
            return
        for picking in self:
            if picking.picking_type_code != 'outgoing':
                raise ValidationError(_('Managed Pengiriman hanya menerima operasi keluar.'))
            for line in picking.move_line_ids_without_package.filtered(lambda item: item.qty_done > 0):
                if line.tracking != 'none' and not line.lot_id and not line.lot_name:
                    raise ValidationError(_('Lot/Serial wajib untuk %(product)s.', product=line.product_id.display_name))
                if line.tracking == 'serial' and line.qty_done > 1:
                    raise ValidationError(_('Satu nomor serial hanya boleh memiliki kuantitas 1 untuk %(product)s.', product=line.product_id.display_name))

    def write(self, vals):
        result = super().write(vals)
        self._check_managed_delivery()
        return result

    def button_validate(self):
        self._check_managed_delivery()
        return super().button_validate()


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def _prepare_picking_default_values(self):
        values = super()._prepare_picking_default_values()
        sequence = self.env['ir.sequence'].sudo().search([
            ('code', '=', f'managed.stock.RTN.{self.picking_id.company_id.id}'),
            ('company_id', '=', self.picking_id.company_id.id),
        ], limit=1)
        if sequence:
            values['name'] = sequence.next_by_id(sequence_date=fields.Datetime.now())
        return values

class ManagedSettingsRegistry(models.AbstractModel):
    _inherit = 'managed.settings.registry'

    @api.model
    def _managed_permission_catalog(self):
        return [
            *super()._managed_permission_catalog(),
            {'key': 'inventory', 'label': 'Persediaan', 'sequence': 50, 'permissions': [
                {'key': 'inventory.deliveries', 'label': 'Pengiriman', 'groups': {
                    'read': 'inventory.group_deliveries_read',
                    'write': 'inventory.group_deliveries_write',
                }},
            ]},
        ]

    @api.model
    def _managed_action_permissions(self):
        return {**super()._managed_action_permissions(), 'inventory.action_deliveries': 'inventory.deliveries'}

    @api.model
    def _managed_menu_permissions(self):
        return {**super()._managed_menu_permissions(), 'inventory.menu_deliveries': 'inventory.deliveries'}
