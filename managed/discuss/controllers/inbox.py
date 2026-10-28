# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re

from odoo import fields, http, tools, _
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request


def _error(message, code='invalid_request', status=400):
    return request.make_json_response({'error': {'code': code, 'message': str(message)}}, status=status, headers=[('Cache-Control', 'no-store')])


def _payload():
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


def _message_data(messages, channel=None):
    current_partner = request.env.user.partner_id
    members = channel.sudo().channel_member_ids if channel else request.env['mail.channel.member']
    other_members = members.filtered(lambda member: member.partner_id and member.partner_id != current_partner)
    result = []
    for message in messages.sorted('id'):
        author = message.author_id.name or message.email_from or _('Sistem')
        mine = message.author_id == current_partner
        receipt = 'sent'
        read_count = 0
        if mine and other_members:
            read_count = len(other_members.filtered(lambda member: member.seen_message_id.id >= message.id))
            fetched_count = len(other_members.filtered(lambda member: member.fetched_message_id.id >= message.id))
            if channel and channel.channel_type != 'chat' and read_count:
                receipt = 'read'
            elif read_count == len(other_members):
                receipt = 'read'
            elif fetched_count == len(other_members):
                receipt = 'delivered'
        reactions = {}
        for reaction in message.sudo().reaction_ids:
            item = reactions.setdefault(reaction.content, {'content': reaction.content, 'count': 0, 'mine': False})
            item['count'] += 1
            item['mine'] = item['mine'] or reaction.partner_id == current_partner
        parent = message.parent_id
        result.append({
            'id': message.id,
            'author': author,
            'authorInitials': _initials(author),
            'body': message.body or '',
            'date': fields.Datetime.to_string(message.date),
            'mine': mine,
            'status': receipt,
            'readCount': read_count,
            'reply': {
                'id': parent.id,
                'author': parent.author_id.name or parent.email_from or _('Sistem'),
                'body': tools.html2plaintext(parent.body or '').strip()[:180],
            } if parent else None,
            'reactions': list(reactions.values()),
            'attachments': [
                {
                    'id': attachment.id, 'name': attachment.name, 'mimetype': attachment.mimetype,
                    'size': attachment.file_size, 'url': f'/mail/channel/{channel.id}/attachment/{attachment.id}?download=1' if channel else f'/web/content/{attachment.id}?download=1',
                    'previewUrl': f'/mail/channel/{channel.id}/image/{attachment.id}' if channel else f'/web/content/{attachment.id}',
                }
                for attachment in message.attachment_ids
            ],
        })
    return result


def _channel_presence(channel):
    members = channel.sudo().channel_member_ids.filtered('partner_id')
    others = members.filtered(lambda member: member.partner_id != request.env.user.partner_id)
    if channel.channel_type == 'chat':
        partner = others[:1].partner_id
        return {
            'otherPartnerId': partner.id or None,
            'presence': partner.im_status if partner else 'offline',
            'onlineCount': int(partner.im_status == 'online') if partner else 0,
        }
    return {
        'otherPartnerId': None,
        'presence': None,
        'onlineCount': len(members.filtered(lambda member: member.partner_id.im_status == 'online')),
    }


def _check_inbox_write():
    if hasattr(request.env.user, '_managed_has_permission') and not request.env.user._managed_has_permission('inbox.messages', 'write'):
        raise AccessError(_('Tidak dapat mengirim atau mengubah pesan.'))


_BLOCKED_ATTACHMENT_EXTENSIONS = {
    'apk', 'app', 'bat', 'cmd', 'com', 'exe', 'gadget', 'hta', 'jar', 'js', 'jse',
    'msi', 'msp', 'pif', 'ps1', 'reg', 'scr', 'sh', 'vbe', 'vbs', 'wsf',
}
_MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
_MAX_ATTACHMENTS = 10


def _document_path(model, record_id):
    mapping = {
        'res.partner': {'customers.action_customers': '/app/contacts/customers', 'vendors.action_vendors': '/app/contacts/vendors'},
        'product.template': {'products.action_products': '/app/products/products'},
        'sale.order': {'sales.action_quotations': '/app/sales/penawaran', 'sales.action_orders': '/app/sales/pesanan'},
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
            'attention': messages + mentions + activities,
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
            channel.channel_fetched()
            return request.make_json_response({
                'channel': {
                    'id': channel.id,
                    'name': member.custom_channel_name or other.name or channel.name,
                    'type': channel.channel_type,
                    'avatarUrl': f'/web/image/res.partner/{other.id}/avatar_128' if other else None,
                    'memberCount': channel.member_count,
                    **_channel_presence(channel),
                },
                'messages': _message_data(messages, channel),
                'firstUnreadId': first_unread.id,
            }, headers=[('Cache-Control', 'no-store')])
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/channels/<int:channel_id>/seen', type='http', auth='user', methods=['POST'])
    def seen(self, channel_id):
        try:
            channel, _member_record = _channel(channel_id)
            message_id = int(_payload().get('messageId') or 0)
            if message_id <= 0:
                return request.make_json_response({'seen': None})
            message = request.env['mail.message'].search([
                ('id', '=', message_id), ('model', '=', 'mail.channel'), ('res_id', '=', channel.id),
            ], limit=1)
            if not message:
                return request.make_json_response({'seen': None})
            channel._channel_seen(message.id)
            return request.make_json_response({'seen': message.id})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError, TypeError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/channels/<int:channel_id>/typing', type='http', auth='user', methods=['POST'])
    def typing(self, channel_id):
        try:
            _check_inbox_write()
            _channel_record, member = _channel(channel_id)
            member.sudo()._notify_typing(bool(_payload().get('typing')))
            return request.make_json_response({'typing': True})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/channels/<int:channel_id>/attachments', type='http', auth='user', methods=['POST'], csrf=True)
    def upload_attachment(self, channel_id, ufile=None, **kw):
        try:
            _check_inbox_write()
            channel, _member_record = _channel(channel_id)
            if not ufile or not ufile.filename:
                raise ValidationError(_('Pilih lampiran.'))
            filename = ufile.filename.rsplit('/', 1)[-1].rsplit('\\', 1)[-1][:255]
            extension = filename.rpartition('.')[2].lower()
            if extension in _BLOCKED_ATTACHMENT_EXTENSIONS:
                raise ValidationError(_('Jenis lampiran tidak diizinkan.'))
            content = ufile.read(_MAX_ATTACHMENT_BYTES + 1)
            if len(content) > _MAX_ATTACHMENT_BYTES:
                raise ValidationError(_('Ukuran lampiran maksimal 25 MB.'))
            attachment = request.env['ir.attachment'].create({
                'name': filename, 'raw': content, 'res_model': 'mail.compose.message', 'res_id': 0,
            })
            attachment._post_add_create()
            return request.make_json_response({
                'attachment': {
                    'id': attachment.id, 'name': attachment.name, 'mimetype': attachment.mimetype,
                    'size': attachment.file_size,
                },
            }, status=201)
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/channels/<int:channel_id>/attachments/delete', type='http', auth='user', methods=['POST'])
    def delete_pending_attachments(self, channel_id):
        try:
            _check_inbox_write()
            _channel(channel_id)
            attachment_ids = _payload().get('attachmentIds') or []
            if not isinstance(attachment_ids, list) or not all(isinstance(item, int) for item in attachment_ids):
                raise ValidationError(_('Lampiran tidak valid.'))
            attachments = request.env['ir.attachment'].sudo().search([
                ('id', 'in', attachment_ids), ('create_uid', '=', request.env.uid),
                ('res_model', '=', 'mail.compose.message'), ('res_id', '=', 0),
            ])
            attachments.unlink()
            return request.make_json_response({'deleted': len(attachments)})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/channels/<int:channel_id>/messages', type='http', auth='user', methods=['POST'])
    def post_message(self, channel_id):
        try:
            _check_inbox_write()
            channel, _member_record = _channel(channel_id)
            payload = _payload()
            body = (payload.get('body') or '').strip()
            attachment_ids = payload.get('attachmentIds') or []
            parent_id = payload.get('parentId')
            request_id = payload.get('requestId')
            if not body and not attachment_ids:
                raise ValidationError(_('Pesan atau lampiran wajib diisi.'))
            if len(body) > 10000:
                raise ValidationError(_('Pesan terlalu panjang.'))
            if not isinstance(attachment_ids, list) or len(attachment_ids) > _MAX_ATTACHMENTS or not all(isinstance(item, int) for item in attachment_ids):
                raise ValidationError(_('Lampiran tidak valid. Maksimal 10 file per pesan.'))
            attachments = request.env['ir.attachment'].sudo().browse(attachment_ids).exists()
            if len(attachments) != len(attachment_ids) or any(
                attachment.create_uid != request.env.user or attachment.res_model != 'mail.compose.message' or attachment.res_id
                for attachment in attachments
            ):
                raise AccessError(_('Lampiran tidak tersedia.'))
            if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9-]{16,64}', request_id):
                raise ValidationError(_('ID pengiriman tidak valid.'))
            message_identifier = f'<managed-inbox-{request_id}@toova>'
            existing = request.env['mail.message'].search([
                ('message_id', '=', message_identifier), ('model', '=', 'mail.channel'), ('res_id', '=', channel.id),
            ], limit=1)
            if existing:
                attachments.unlink()
                return request.make_json_response({'message': _message_data(existing, channel)[0]}, status=200)
            parent = request.env['mail.message']
            if parent_id:
                parent = request.env['mail.message'].search([
                    ('id', '=', int(parent_id)), ('model', '=', 'mail.channel'), ('res_id', '=', channel.id),
                ], limit=1)
                if not parent:
                    raise ValidationError(_('Pesan balasan tidak tersedia.'))
            with request.env.cr.savepoint():
                message = channel.message_post(
                    body=tools.plaintext2html(body) if body else '', attachment_ids=attachment_ids,
                    parent_id=parent.id, message_id=message_identifier,
                    message_type='comment', subtype_xmlid='mail.mt_comment',
                )
            return request.make_json_response({'message': _message_data(message, channel)[0]}, status=201)
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError, TypeError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/channels/<int:channel_id>/messages/<int:message_id>/reaction', type='http', auth='user', methods=['POST'])
    def reaction(self, channel_id, message_id):
        try:
            _check_inbox_write()
            channel, _member_record = _channel(channel_id)
            message = request.env['mail.message'].search([
                ('id', '=', message_id), ('model', '=', 'mail.channel'), ('res_id', '=', channel.id),
            ], limit=1)
            if not message:
                raise MissingError(_('Pesan tidak tersedia.'))
            content = (_payload().get('content') or '').strip()
            if not content or len(content) > 16:
                raise ValidationError(_('Reaction tidak valid.'))
            own = message.sudo().reaction_ids.filtered(
                lambda item: item.partner_id == request.env.user.partner_id and item.content == content
            )
            if own:
                message._message_remove_reaction(content)
            else:
                message._message_add_reaction(content)
            return request.make_json_response({'message': _message_data(message, channel)[0]})
        except (AccessError, MissingError) as error:
            return _error(error, 'forbidden', 403)
        except (UserError, ValidationError, ValueError) as error:
            return _error(error)

    @http.route('/api/v1/inbox/direct', type='http', auth='user', methods=['POST'])
    def direct(self):
        try:
            _check_inbox_write()
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
            if len(name) > 120:
                raise ValidationError(_('Nama channel terlalu panjang.'))
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
