# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, http, tools, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request


def _error(message, code='invalid_request', status=400):
    return request.make_json_response({'error': {'code': code, 'message': str(message)}}, status=status, headers=[('Cache-Control', 'no-store')])


def _payload():
    import json
    value = request.params.get('payload')
    if not value:
        return {}
    try:
        value = json.loads(value)
    except (TypeError, ValueError) as error:
        raise ValidationError(_('Payload tidak valid.')) from error
    if not isinstance(value, dict):
        raise ValidationError(_('Payload harus berupa object.'))
    return value


def _member(channel_id):
    return request.env['mail.channel.member'].sudo().search([
        ('channel_id', '=', int(channel_id)),
        ('partner_id', '=', request.env.user.partner_id.id),
    ], limit=1)


def _channel(channel_id):
    member = _member(channel_id)
    if not member:
        raise AccessError(_('Channel tidak tersedia.'))
    return member.channel_id.sudo(False), member


def _initials(value):
    return ''.join(part[:1] for part in (value or '?').split()[:2]).upper()


def _message_data(messages):
    result = []
    for message in messages.sorted('id'):
        author = message.author_id.name or message.email_from or _('Sistem')
        result.append({
            'id': message.id,
            'author': author,
            'authorInitials': _initials(author),
            'body': message.body or '',
            'date': fields.Datetime.to_string(message.date),
            'mine': message.author_id == request.env.user.partner_id,
            'attachments': [
                {'id': attachment.id, 'name': attachment.name, 'mimetype': attachment.mimetype, 'size': attachment.file_size}
                for attachment in message.attachment_ids
            ],
        })
    return result


def _document_path(model, record_id):
    mapping = {
        'res.partner': {'customers.action_customers': '/app/contacts/customers', 'vendors.action_vendors': '/app/contacts/vendors'},
        'product.template': {'products.action_products': '/app/products/products'},
        'sale.order': {'sale.action_quotations': '/app/sales/penawaran', 'sale.action_orders': '/app/sales/pesanan-penjualan'},
    }
    candidates = mapping.get(model, {})
    for xmlid, base in candidates.items():
        action = request.env.ref(xmlid, raise_if_not_found=False)
        if action:
            return f'{base}/{record_id}'
    return None


class ManagedInboxApi(http.Controller):

    def _counts(self):
        partner = request.env.user.partner_id
        members = request.env['mail.channel.member'].sudo().search([
            ('partner_id', '=', partner.id),
            ('is_pinned', '=', True),
        ])
        messages = sum(members.mapped('message_unread_counter'))
        mentions = request.env['mail.message'].search_count([('needaction', '=', True)])
        activities = request.env['mail.activity'].search_count([
            ('user_id', '=', request.env.uid),
            ('date_deadline', '<=', fields.Date.context_today(request.env['mail.activity'])),
        ])
        return {
            'messages': messages,
            'mentions': mentions,
            'activities': activities,
            'attention': mentions + activities,
        }

    @http.route('/api/v1/inbox/counts', type='http', auth='user', methods=['GET'])
    def counts(self):
        try:
            return request.make_json_response(self._counts(), headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox', type='http', auth='user', methods=['GET'])
    def overview(self):
        try:
            partner = request.env.user.partner_id
            members = request.env['mail.channel.member'].sudo().search([
                ('partner_id', '=', partner.id),
                ('is_pinned', '=', True),
            ], order='last_interest_dt desc, id desc')
            channels = members.mapped('channel_id').sudo(False)
            previews = {item['id']: item.get('last_message') for item in channels.channel_fetch_preview()}
            conversations = []
            for member in members:
                channel = member.channel_id
                preview = previews.get(channel.id) or {}
                author = preview.get('author') or {}
                other = channel.channel_member_ids.filtered(
                    lambda item: item.partner_id and item.partner_id != partner
                )[:1].partner_id if channel.channel_type == 'chat' else request.env['res.partner']
                conversations.append({
                    'id': channel.id,
                    'name': member.custom_channel_name or other.name or channel.name,
                    'type': channel.channel_type,
                    'unread': member.message_unread_counter,
                    'date': preview.get('date') or fields.Datetime.to_string(member.last_interest_dt),
                    'preview': tools.html2plaintext(preview.get('body') or '').strip()[:140],
                    'author': author.get('name') if isinstance(author, dict) else False,
                    'avatarUrl': f'/web/image/res.partner/{other.id}/avatar_128' if other else None,
                    'memberCount': channel.member_count,
                })
            activities = request.env['mail.activity'].search([('user_id', '=', request.env.uid)], order='date_deadline asc, id asc', limit=30)
            activity_data = [{
                'id': activity.id,
                'summary': activity.summary or activity.activity_type_id.name,
                'record': activity.res_name,
                'model': activity.res_model,
                'resId': activity.res_id,
                'deadline': fields.Date.to_string(activity.date_deadline),
                'state': activity.state,
                'path': _document_path(activity.res_model, activity.res_id),
            } for activity in activities]
            mentions = request.env['mail.message']._message_fetch([('needaction', '=', True)], limit=30)
            mention_data = [{
                'id': message.id,
                'author': message.author_id.name or message.email_from or _('Sistem'),
                'preview': tools.html2plaintext(message.body or '').strip()[:180],
                'record': message.record_name,
                'date': fields.Datetime.to_string(message.date),
                'path': _document_path(message.model, message.res_id),
            } for message in mentions]
            return request.make_json_response({
                'conversations': conversations,
                'activities': activity_data,
                'mentions': mention_data,
                'counts': self._counts(),
                'canManageChannels': request.env.user.has_group('discuss.group_channel_manage_write'),
            }, headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/channels/<int:channel_id>', type='http', auth='user', methods=['GET'])
    def thread(self, channel_id, before=None, **kw):
        try:
            channel, member = _channel(channel_id)
            domain = [('model', '=', 'mail.channel'), ('res_id', '=', channel.id), ('message_type', 'not in', ('notification', 'user_notification'))]
            if before and str(before).isdigit():
                domain.append(('id', '<', int(before)))
            messages = request.env['mail.message'].search(domain, order='id desc', limit=50)
            previous_seen_id = member.seen_message_id.id
            first_unread = messages.filtered(lambda message: message.id > previous_seen_id).sorted('id')[:1]
            other = channel.channel_member_ids.filtered(
                lambda item: item.partner_id and item.partner_id != request.env.user.partner_id
            )[:1].partner_id if channel.channel_type == 'chat' else request.env['res.partner']
            if messages:
                channel._channel_seen(messages[0].id)
            return request.make_json_response({
                'channel': {
                    'id': channel.id,
                    'name': member.custom_channel_name or other.name or channel.name,
                    'type': channel.channel_type,
                    'avatarUrl': f'/web/image/res.partner/{other.id}/avatar_128' if other else None,
                    'memberCount': channel.member_count,
                },
                'messages': _message_data(messages),
                'firstUnreadId': first_unread.id,
            }, headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/channels/<int:channel_id>/messages', type='http', auth='user', methods=['POST'])
    def post_message(self, channel_id):
        try:
            channel, _member_record = _channel(channel_id)
            body = (_payload().get('body') or '').strip()
            if not body:
                raise ValidationError(_('Pesan tidak boleh kosong.'))
            if len(body) > 10000:
                raise ValidationError(_('Pesan terlalu panjang.'))
            message = channel.message_post(body=tools.plaintext2html(body), message_type='comment', subtype_xmlid='mail.mt_comment')
            return request.make_json_response({'message': _message_data(message)[0]}, status=201)
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/direct', type='http', auth='user', methods=['POST'])
    def direct(self):
        try:
            partner_id = _payload().get('partnerId')
            partner = request.env['res.partner'].browse(int(partner_id or 0)).exists()
            if not partner or not partner.user_ids.filtered(lambda user: user.active and not user.share):
                raise ValidationError(_('Pengguna tidak tersedia.'))
            info = request.env['mail.channel'].channel_get([partner.id])
            return request.make_json_response({'channelId': info['id']}, status=201)
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError, TypeError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/partners', type='http', auth='user', methods=['GET'])
    def partners(self, q='', **kw):
        domain = [('active', '=', True), ('share', '=', False), ('id', '!=', request.env.uid)]
        if q:
            domain += ['|', ('name', 'ilike', q), ('login', 'ilike', q)]
        users = request.env['res.users'].sudo().search(domain, order='name', limit=20)
        return request.make_json_response({'items': [{
            'id': user.partner_id.id,
            'label': user.name,
            'email': user.login,
            'avatarUrl': f'/web/image/res.partner/{user.partner_id.id}/avatar_128',
        } for user in users]})

    @http.route('/api/v1/inbox/channels', type='http', auth='user', methods=['POST'])
    def create_channel(self):
        try:
            if not request.env.user.has_group('discuss.group_channel_manage_write'):
                raise AccessError(_('Tidak dapat membuat channel.'))
            payload = _payload()
            name = (payload.get('name') or '').strip()
            visibility = payload.get('visibility') or 'private'
            partner_ids = payload.get('partnerIds') or []
            if not name:
                raise ValidationError(_('Nama channel wajib diisi.'))
            if visibility not in {'public', 'private'} or not isinstance(partner_ids, list) or not all(isinstance(item, int) for item in partner_ids):
                raise ValidationError(_('Pengaturan channel tidak valid.'))
            if visibility == 'public':
                partner_ids = request.env['res.users'].sudo().search([
                    ('active', '=', True), ('share', '=', False),
                ]).mapped('partner_id').ids
            else:
                valid = request.env['res.users'].sudo().search([
                    ('active', '=', True), ('share', '=', False), ('partner_id', 'in', partner_ids),
                ]).mapped('partner_id').ids
                if set(valid) != set(partner_ids):
                    raise ValidationError(_('Anggota channel tidak valid.'))
                partner_ids = valid + [request.env.user.partner_id.id]
            channel = request.env['mail.channel'].create({
                'name': name,
                'channel_type': 'channel' if visibility == 'public' else 'group',
            })
            channel.add_members(list(set(partner_ids)), post_joined_message=False)
            return request.make_json_response({'channelId': channel.id}, status=201)
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/activities/<int:activity_id>/done', type='http', auth='user', methods=['POST'])
    def complete_activity(self, activity_id):
        try:
            activity = request.env['mail.activity'].browse(activity_id).exists()
            if not activity or activity.user_id != request.env.user:
                raise AccessError(_('Aktivitas tidak tersedia.'))
            activity.action_feedback()
            return request.make_json_response({'done': True})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)
