# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.osv import expression


def _error(error, status=400):
    return request.make_json_response(
        {'error': {'code': 'forbidden' if status == 403 else 'invalid_request', 'message': str(error)}},
        status=status,
        headers=[('Cache-Control', 'no-store')],
    )


class ManagedWarehouseApi(http.Controller):

    @http.route('/api/v1/warehouse/operations', type='http', auth='user', methods=['GET'])
    def operations(self, scope='open', **kw):
        try:
            if not request.env.user._managed_has_permission('inventory.deliveries', 'read'):
                raise AccessError('Akses Operasi Gudang tidak tersedia.')
            domain = [('company_id', '=', request.env.company.id), ('state', '!=', 'cancel')]
            if scope == 'done':
                domain = expression.AND([domain, [('state', '=', 'done'), ('date_done', '>=', fields.Date.today())]])
            else:
                domain = expression.AND([domain, [('state', '!=', 'done')]])
            pickings = request.env['stock.picking'].search(domain, order='priority desc, scheduled_date asc, id asc', limit=80)
            items = [{
                'id': picking.id,
                'name': picking.name,
                'kind': picking.managed_operation_kind,
                'status': picking.managed_operation_status,
                'progress': picking.managed_operation_progress,
                'partner': picking.partner_id.display_name or '',
                'origin': picking.origin or '',
                'scheduledDate': picking.scheduled_date,
                'source': picking.location_id.display_name,
                'destination': picking.location_dest_id.display_name,
                'state': picking.state,
                'late': bool(picking.scheduled_date and picking.scheduled_date < fields.Datetime.now()),
            } for picking in pickings]
            counts = {
                'ready': len(pickings.filtered(lambda item: item.state == 'assigned')),
                'waiting': len(pickings.filtered(lambda item: item.state in ('waiting', 'confirmed', 'partially_available'))),
                'late': len(pickings.filtered(lambda item: item.scheduled_date and item.scheduled_date < fields.Datetime.now())),
                'total': len(pickings),
            }
            return request.make_json_response({'items': items, 'counts': counts}, headers=[('Cache-Control', 'no-store')])
        except AccessError as error:
            return _error(error, 403)
