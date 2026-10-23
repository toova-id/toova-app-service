# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class SaleApi(http.Controller):

    @http.route('/api/v1/sales/orders', type='http', auth='user', methods=['GET'])
    def orders(self, page=1, q='', **kw):
        if not request.env.user._is_internal():
            raise AccessError('Internal access required.')
        try:
            page = max(int(page), 1)
        except (TypeError, ValueError):
            return request.make_json_response(
                {'error': {'code': 'invalid_page', 'message': 'Page must be a positive integer.'}},
                status=400,
            )

        page_size = 25
        domain = []
        if q:
            domain = ['|', ('name', 'ilike', q), ('partner_id.name', 'ilike', q)]
        orders = request.env['sale.order'].search(
            domain, order='date_order desc, id desc', limit=page_size, offset=(page - 1) * page_size,
        )
        state_labels = dict(request.env['sale.order']._fields['state']._description_selection(request.env))
        return request.make_json_response({
            'items': [{
                'id': order.id,
                'name': order.name,
                'customer': order.partner_id.display_name,
                'date': order.date_order.isoformat() if order.date_order else None,
                'state': order.state,
                'stateLabel': state_labels.get(order.state, order.state),
                'total': order.amount_total,
                'currency': order.currency_id.name,
            } for order in orders],
            'page': page,
            'pageSize': page_size,
            'total': request.env['sale.order'].search_count(domain),
        }, headers=[('Cache-Control', 'no-store')])
