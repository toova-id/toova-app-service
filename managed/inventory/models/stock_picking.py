# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    managed_demand_qty = fields.Float(related='move_id.product_uom_qty', string='Permintaan', readonly=True)


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
                            {'name': 'company_id', 'label': 'Perusahaan'},
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
                    {'name': 'company_id', 'label': 'Perusahaan'},
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
