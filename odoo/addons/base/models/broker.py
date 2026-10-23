# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import json
import logging
import re
import time
import uuid
from datetime import timedelta

from odoo import api, fields, models, SUPERUSER_ID, Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import config, safe_eval
from odoo.broker.api import registered_handlers, validate_topic

_logger = logging.getLogger(__name__)
_CHANNEL_RE = re.compile(r'^[A-Za-z0-9._-]+$')


def _pretty_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) if value is not False else ''


def _physical_topic(topic):
    if topic.physical_name_mode == 'exact':
        return topic.physical_topic or topic.name
    prefix = config['broker_topic_prefix'].strip('.-_ ')
    name = topic.physical_topic or topic.name
    return f'{prefix}.{name}' if prefix else name


def _validate_path(path):
    if path and any(not part for part in path.split('.')):
        raise ValueError(_('JSON paths must use non-empty dot-separated keys.'))


def _path_value(value, path):
    """Resolve a deliberately small dot path without adding a JSONPath dependency."""
    if not path:
        return value
    _validate_path(path)
    for part in path.split('.'):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            raise KeyError(path)
    return value


class BrokerTopic(models.Model):
    _name = 'broker.topic'
    _description = 'Broker Topic'
    _order = 'name'

    name = fields.Char(required=True, index=True, help='Stable logical name used by Odoo code.')
    description = fields.Text()
    active = fields.Boolean(default=True)
    provider = fields.Selection([('nsq', 'NSQ')], required=True, default='nsq')
    ownership = fields.Selection([
        ('internal', 'Managed by Odoo'),
        ('external', 'Managed Externally'),
    ], required=True, default='internal')
    direction = fields.Selection([
        ('inbound', 'Inbound'),
        ('outbound', 'Outbound'),
        ('both', 'Inbound and Outbound'),
    ], required=True, default='both')
    physical_name_mode = fields.Selection([
        ('prefixed', 'Apply Odoo Prefix'),
        ('exact', 'Use Exact Name'),
    ], required=True, default='prefixed')
    physical_topic = fields.Char(help='Transport topic. Empty uses the logical name.')
    physical_topic_display = fields.Char(compute='_compute_physical_topic_display', string='Physical Topic')
    message_format = fields.Selection([
        ('odoo', 'Odoo Envelope'),
        ('json', 'JSON'),
        ('raw', 'Raw UTF-8'),
    ], required=True, default='odoo')
    message_id_path = fields.Char(
        help='Dot path containing a stable external event ID. Transport ID or payload hash is the fallback.')
    event_type_path = fields.Char(help='Optional dot path containing the external event type.')
    payload_path = fields.Char(help='Optional dot path selecting data passed to the handler.')
    max_payload_bytes = fields.Integer(default=1048576, required=True)
    store_payload = fields.Boolean(
        default=True,
        help='Store received payloads in delivery logs. Disable for sensitive data; handlers still receive the payload.')
    max_retries = fields.Integer(default=lambda self: config['broker_max_retries'], required=True)
    retry_delay = fields.Integer(default=30, required=True, help='Retry delay in seconds.')
    dead_letter_topic = fields.Char(help='Logical topic receiving exhausted messages.')
    subscription_ids = fields.One2many('broker.subscription', 'topic_id', string='Channels')
    subscription_count = fields.Integer(compute='_compute_counts')
    outbox_count = fields.Integer(compute='_compute_counts')
    outbox_failed_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [('broker_topic_name_uniq', 'unique(name)', 'Broker topic must be unique.')]

    @api.depends('physical_name_mode', 'physical_topic', 'name')
    def _compute_physical_topic_display(self):
        for topic in self:
            topic.physical_topic_display = _physical_topic(topic) if topic.name else False

    def _broker_display_name(self):
        self.ensure_one()
        physical = self.physical_topic_display
        return f'{self.name} [{physical}]' if physical and physical != self.name else (self.name or '')

    @api.depends('name', 'physical_name_mode', 'physical_topic')
    def _compute_display_name(self):
        for topic in self:
            topic.display_name = topic._broker_display_name()

    def name_get(self):
        return [(topic.id, topic._broker_display_name()) for topic in self]

    def _compute_counts(self):
        for topic in self:
            topic.subscription_count = self.env['broker.subscription'].search_count([('topic_id', '=', topic.id)])
            topic.outbox_count = self.env['broker.outbox'].search_count([('topic_id', '=', topic.id)])
            topic.outbox_failed_count = self.env['broker.outbox'].search_count([
                ('topic_id', '=', topic.id), ('state', '=', 'failed'),
            ])

    @api.constrains(
        'name', 'physical_topic', 'physical_name_mode', 'dead_letter_topic',
        'max_retries', 'retry_delay', 'max_payload_bytes', 'message_id_path',
        'event_type_path', 'payload_path',
    )
    def _check_values(self):
        for record in self:
            try:
                validate_topic(record.name)
                if record.physical_topic:
                    validate_topic(record.physical_topic)
                if record.dead_letter_topic:
                    validate_topic(record.dead_letter_topic)
                for path in (record.message_id_path, record.event_type_path, record.payload_path):
                    _validate_path(path)
            except ValueError as error:
                raise ValidationError(str(error)) from error
            if record.physical_name_mode == 'exact' and not record.physical_topic:
                raise ValidationError(_('Exact physical topic mode requires a physical topic.'))
            if record.max_retries < 0 or record.retry_delay < 0:
                raise ValidationError(_('Retry values cannot be negative.'))
            if record.max_payload_bytes < 1:
                raise ValidationError(_('Maximum payload size must be positive.'))

    @api.model
    def _ensure(self, name, for_publish=True):
        validate_topic(name)
        topic = self.sudo().search([('name', '=', name)], limit=1)
        if not topic:
            topic = self.sudo().create({'name': name})
        if not topic.active:
            raise UserError(_('Broker topic %s is paused.', name))
        if for_publish and topic.direction == 'inbound':
            raise UserError(_('Broker topic %s is inbound only.', name))
        return topic

    def action_open_channels(self):
        self.ensure_one()
        action = self.env.ref('base.broker_subscription_action').read()[0]
        action['domain'] = [('topic_id', '=', self.id)]
        action['context'] = {'default_topic_id': self.id}
        return action

    def action_open_outbox(self):
        self.ensure_one()
        action = self.env.ref('base.broker_outbox_action').read()[0]
        action['domain'] = [('topic_id', '=', self.id)]
        return action

    def action_open_failed_outbox(self):
        action = self.action_open_outbox()
        action['domain'] = [('topic_id', '=', self.id), ('state', '=', 'failed')]
        return action


class BrokerSubscription(models.Model):
    _name = 'broker.subscription'
    _description = 'Broker Channel'
    _order = 'topic_id, channel'
    _rec_name = 'channel'

    topic_id = fields.Many2one('broker.topic', required=True, ondelete='cascade', index=True)
    channel = fields.Char(required=True, default='odoo')
    active = fields.Boolean(default=True)
    handler_type = fields.Selection([
        ('registry', 'Registered Python Handler'),
        ('code', 'Execute Python Code'),
    ], required=True, default='registry')
    handler = fields.Char(help='Trusted handler registered by an installed Python addon.')
    model_id = fields.Many2one('ir.model', string='Model', ondelete='cascade')
    code = fields.Text(string='Python Code', groups='base.group_system', default="""# Available variables:
#  env, model, record, records
#  message, payload, topic, channel
#  time, datetime, dateutil, UserError, Command
#  log(message, level='info')

""")
    user_id = fields.Many2one(
        'res.users', required=True, default=lambda self: self.env.ref('base.user_root'),
        help='Execution identity. External payloads cannot override it.')
    company_id = fields.Many2one('res.company', help='Optional fixed execution company.')
    max_in_flight = fields.Integer(default=10, required=True)
    inbox_ids = fields.One2many('broker.inbox', 'subscription_id', string='Deliveries')
    delivery_count = fields.Integer(compute='_compute_delivery_counts')
    failed_count = fields.Integer(compute='_compute_delivery_counts')
    dead_count = fields.Integer(compute='_compute_delivery_counts')
    last_received_at = fields.Datetime(compute='_compute_delivery_counts')

    _sql_constraints = [('broker_subscription_uniq', 'unique(topic_id, channel)', 'Topic/channel must be unique.')]

    def _compute_delivery_counts(self):
        for channel in self:
            deliveries = self.env['broker.inbox'].search([('subscription_id', '=', channel.id)])
            channel.delivery_count = len(deliveries)
            channel.failed_count = len(deliveries.filtered(lambda item: item.state == 'failed'))
            channel.dead_count = len(deliveries.filtered(lambda item: item.state == 'dead'))
            channel.last_received_at = deliveries[:1].received_at if deliveries else False

    def _broker_display_name(self):
        self.ensure_one()
        return f'{self.topic_id.name} / {self.channel}' if self.topic_id else (self.channel or '')

    @api.depends('topic_id.name', 'channel')
    def _compute_display_name(self):
        for channel in self:
            channel.display_name = channel._broker_display_name()

    def name_get(self):
        return [(channel.id, channel._broker_display_name()) for channel in self]

    @api.constrains('channel', 'handler_type', 'handler', 'code', 'model_id', 'max_in_flight')
    def _check_values(self):
        handlers = registered_handlers()
        for record in self:
            if not record.channel or len(record.channel) > 64 or not _CHANNEL_RE.fullmatch(record.channel):
                raise ValidationError(_('Broker channel has invalid characters.'))
            if record.handler_type == 'registry':
                if not record.handler:
                    raise ValidationError(_('Registered handler is required.'))
                try:
                    validate_topic(record.handler)
                except ValueError as error:
                    raise ValidationError(str(error)) from error
                # Installed code may register after data loading; runtime reports missing handlers.
                if record.active and handlers and record.handler not in handlers:
                    _logger.warning('Broker handler %s is not currently registered.', record.handler)
            elif record.handler_type == 'code':
                if not record.model_id:
                    raise ValidationError(_('A model is required for Python channel actions.'))
                message = safe_eval.test_python_expr(expr=(record.code or '').strip(), mode='exec')
                if message:
                    raise ValidationError(message)
            if record.max_in_flight < 1:
                raise ValidationError(_('Max in flight must be positive.'))

    @api.model
    def _runtime_definitions(self):
        handlers = registered_handlers()
        subscriptions = self.sudo().search([
            ('active', '=', True),
            ('topic_id.active', '=', True),
            ('topic_id.direction', 'in', ('inbound', 'both')),
        ])
        definitions = []
        for subscription in subscriptions:
            if subscription.handler_type == 'registry' and subscription.handler not in handlers:
                _logger.warning('Broker handler %s is not registered; channel skipped.', subscription.handler)
                continue
            definitions.append({
                'id': subscription.id,
                'physical_topic': _physical_topic(subscription.topic_id),
                'channel': subscription.channel,
                'max_in_flight': subscription.max_in_flight,
            })
        return definitions

    def _execution_log(self, message, level='info', user_id=None):
        self.ensure_one()
        level = str(level).upper()
        if level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            level = 'INFO'
        with self.pool.cursor() as cr:
            cr.execute("""
                INSERT INTO ir_logging
                    (create_date, create_uid, type, dbname, name, level, message, path, line, func)
                VALUES
                    (NOW() AT TIME ZONE 'UTC', %s, 'server', %s, 'broker.channel', %s, %s,
                     'broker.subscription', %s, %s)
            """, (user_id or self.env.uid, self.env.cr.dbname, level, str(message), self.id,
                  '%s/%s' % (self.topic_id.name, self.channel)))

    def _run_code(self, env, message):
        self.ensure_one()
        model = env[self.model_id.model]
        record_ids = message.get('record_ids') or []
        records = model.browse(record_ids).exists() if record_ids else model
        if record_ids:
            model.check_access_rights('write')
            records.check_access_rule('write')
        context = {
            'env': env,
            'model': model,
            'record': records[:1] if record_ids else model,
            'records': records,
            'message': message,
            'payload': message.get('payload'),
            'topic': self.topic_id,
            'channel': self,
            'time': safe_eval.time,
            'datetime': safe_eval.datetime,
            'dateutil': safe_eval.dateutil,
            'UserError': UserError,
            'Command': Command,
            'log': lambda message, level='info': self._execution_log(message, level, env.uid),
        }
        safe_eval.safe_eval((self.code or '').strip(), context, mode='exec', nocopy=True, filename=str(self))

    def _execute(self, env, message):
        self.ensure_one()
        if self.handler_type == 'code':
            return self._run_code(env, message)
        handler = registered_handlers().get(self.handler)
        if handler is None:
            raise UserError(_('Broker handler %s is not registered.', self.handler))
        return handler(env, message)

    def action_open_deliveries(self):
        self.ensure_one()
        action = self.env.ref('base.broker_inbox_action').read()[0]
        action['domain'] = [('subscription_id', '=', self.id)]
        return action

    def action_open_failed(self):
        action = self.action_open_deliveries()
        action['domain'] = [('subscription_id', '=', self.id), ('state', '=', 'failed')]
        return action

    def action_open_dead(self):
        action = self.action_open_deliveries()
        action['domain'] = [('subscription_id', '=', self.id), ('state', '=', 'dead')]
        return action

    def action_open_logs(self):
        self.ensure_one()
        action = self.env.ref('base.ir_logging_all_act').read()[0]
        action['domain'] = [('path', '=', 'broker.subscription'), ('line', '=', str(self.id))]
        return action


class BrokerPublisher(models.AbstractModel):
    _name = 'broker.publisher'
    _description = 'Broker Publisher'

    @api.model
    def publish(self, topic, payload=None, *, record_ids=None, key=None, user_id=None, company_id=None):
        payload = payload if payload is not None else {}
        try:
            json.dumps(payload)
        except (TypeError, ValueError) as error:
            raise ValidationError(_('Broker payload must be JSON serializable.')) from error
        record_ids = list(record_ids or [])
        if not all(isinstance(record_id, int) and not isinstance(record_id, bool) for record_id in record_ids):
            raise ValidationError(_('Broker record IDs must be integers.'))
        if key is not None and not isinstance(key, str):
            raise ValidationError(_('Broker key must be a string.'))
        topic_record = self.env['broker.topic']._ensure(topic, for_publish=True)
        if topic_record.message_format == 'odoo' and not isinstance(payload, dict):
            raise ValidationError(_('Odoo envelope payload must be a JSON object.'))
        if topic_record.message_format == 'raw' and not isinstance(payload, str):
            raise ValidationError(_('Raw broker payload must be a string.'))
        message_id = str(uuid.uuid4())
        values = {
            'message_id': message_id,
            'topic_id': topic_record.id,
            'key': key,
            'user_id': user_id or self.env.uid,
            'company_id': company_id or self.env.company.id,
            'record_ids': record_ids,
            'payload': payload,
        }
        self.env['broker.outbox'].sudo().create(values)
        return message_id


class BrokerOutbox(models.Model):
    _name = 'broker.outbox'
    _description = 'Broker Transactional Outbox'
    _rec_name = 'message_id'
    _order = 'id desc'

    message_id = fields.Char(required=True, index=True, readonly=True)
    topic_id = fields.Many2one('broker.topic', required=True, ondelete='restrict', readonly=True)
    key = fields.Char(readonly=True)
    user_id = fields.Many2one('res.users', required=True, readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    record_ids = fields.Json(readonly=True)
    record_ids_display = fields.Text(compute='_compute_json_display', string='Record IDs')
    payload = fields.Json(readonly=True)
    payload_display = fields.Text(compute='_compute_json_display', string='Payload')
    body_override = fields.Text(readonly=True, help='Exact transport body used only for operational replay.')
    state = fields.Selection([
        ('pending', 'Pending'),
        ('publishing', 'Publishing'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ], default='pending', required=True, index=True, readonly=True)
    attempt_count = fields.Integer(default=0, readonly=True)
    next_attempt_at = fields.Datetime(default=fields.Datetime.now, index=True, readonly=True)
    published_at = fields.Datetime(readonly=True)
    last_error = fields.Text(readonly=True)

    _sql_constraints = [('broker_outbox_message_uniq', 'unique(message_id)', 'Message ID must be unique.')]

    @api.depends('payload', 'record_ids')
    def _compute_json_display(self):
        for message in self:
            message.payload_display = _pretty_json(message.payload)
            message.record_ids_display = _pretty_json(message.record_ids)

    def _broker_display_name(self):
        self.ensure_one()
        return f'{self.topic_id.name} / {self.message_id}' if self.topic_id else (self.message_id or '')

    @api.depends('topic_id.name', 'message_id')
    def _compute_display_name(self):
        for message in self:
            message.display_name = message._broker_display_name()

    def name_get(self):
        return [(message.id, message._broker_display_name()) for message in self]

    @api.model
    def _claim_batch(self, limit):
        now = fields.Datetime.now()
        stale = now - timedelta(minutes=5)
        self.env.cr.execute('''
            SELECT id FROM broker_outbox
             WHERE (state IN ('pending', 'failed') AND next_attempt_at <= %s)
                OR (state = 'publishing' AND write_date <= %s)
             ORDER BY id
             FOR UPDATE SKIP LOCKED
             LIMIT %s
        ''', [now, stale, limit])
        records = self.browse([row[0] for row in self.env.cr.fetchall()])
        records.write({'state': 'publishing'})
        return [{
            'id': record.id,
            'physical_topic': _physical_topic(record.topic_id),
            'body': record._serialized_body(),
        } for record in records]

    def _envelope(self):
        self.ensure_one()
        return {
            'id': self.message_id,
            'database': self.env.cr.dbname,
            'topic': self.topic_id.name,
            'version': 1,
            'created_at': fields.Datetime.to_string(self.create_date),
            'key': self.key,
            'user_id': self.user_id.id,
            'company_id': self.company_id.id or None,
            'record_ids': self.record_ids or [],
            'payload': self.payload or {},
        }

    def _serialized_body(self):
        self.ensure_one()
        if self.body_override:
            return self.body_override
        if self.topic_id.message_format == 'odoo':
            return json.dumps(self._envelope())
        if self.topic_id.message_format == 'raw':
            return self.payload
        return json.dumps(self.payload)

    @api.model
    def _mark_published(self, record_id):
        record = self.browse(record_id).exists()
        if record:
            record.write({'state': 'published', 'published_at': fields.Datetime.now(), 'last_error': False})

    @api.model
    def _mark_failed(self, record_id, error):
        record = self.browse(record_id).exists()
        if record:
            attempts = record.attempt_count + 1
            delay = min(2 ** min(attempts, 10), 900)
            record.write({
                'state': 'failed', 'attempt_count': attempts,
                'next_attempt_at': fields.Datetime.now() + timedelta(seconds=delay),
                'last_error': error[:4000],
            })

    @api.autovacuum
    def _gc_published(self):
        cutoff = fields.Datetime.now() - timedelta(days=7)
        self.search([('state', '=', 'published'), ('published_at', '<', cutoff)]).unlink()


class BrokerInbox(models.Model):
    _name = 'broker.inbox'
    _description = 'Broker Delivery Log'
    _rec_name = 'message_id'
    _order = 'id desc'

    message_id = fields.Char(required=True, index=True, readonly=True)
    transport_message_id = fields.Char(index=True, readonly=True)
    subscription_id = fields.Many2one('broker.subscription', required=True, ondelete='cascade', readonly=True)
    topic_id = fields.Many2one(related='subscription_id.topic_id', store=True, readonly=True)
    physical_topic = fields.Char(readonly=True)
    event_type = fields.Char(index=True, readonly=True)
    state = fields.Selection([
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('skipped', 'Skipped'),
        ('failed', 'Failed'),
        ('dead', 'Dead Letter'),
    ], required=True, default='processing', index=True, readonly=True)
    attempt_count = fields.Integer(default=0, readonly=True)
    payload = fields.Json(readonly=True)
    payload_display = fields.Text(compute='_compute_payload_display', string='Payload')
    raw_body = fields.Text(readonly=True)
    replayable = fields.Boolean(readonly=True)
    payload_size = fields.Integer(readonly=True)
    received_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    last_attempt_at = fields.Datetime(readonly=True)
    processed_at = fields.Datetime(readonly=True)
    duration_ms = fields.Float(readonly=True)
    last_error = fields.Text(readonly=True)

    _sql_constraints = [(
        'broker_inbox_message_subscription_uniq',
        'unique(message_id, subscription_id)',
        'Message was already processed for this channel.',
    )]

    @api.depends('payload')
    def _compute_payload_display(self):
        for delivery in self:
            delivery.payload_display = _pretty_json(delivery.payload)

    def _broker_display_name(self):
        self.ensure_one()
        if self.subscription_id:
            return f'{self.subscription_id.topic_id.name} / {self.subscription_id.channel} / {self.message_id}'
        return self.message_id or ''

    @api.depends('subscription_id.topic_id.name', 'subscription_id.channel', 'message_id')
    def _compute_display_name(self):
        for delivery in self:
            delivery.display_name = delivery._broker_display_name()

    def name_get(self):
        return [(delivery.id, delivery._broker_display_name()) for delivery in self]

    @api.model
    def _validate_internal_envelope(self, envelope):
        if not isinstance(envelope, dict) or envelope.get('version') != 1:
            raise ValidationError(_('Invalid broker envelope version.'))
        validate_topic(envelope.get('topic'))
        try:
            uuid.UUID(envelope.get('id'))
        except (TypeError, ValueError) as error:
            raise ValidationError(_('Invalid broker message ID.')) from error
        if envelope.get('database') != self.env.cr.dbname:
            raise ValidationError(_('Broker message database mismatch.'))
        if not isinstance(envelope.get('payload', {}), dict) or not isinstance(envelope.get('record_ids', []), list):
            raise ValidationError(_('Invalid broker message payload.'))

    @api.model
    def _normalize_message(self, subscription, body, transport_message_id=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        if not isinstance(body, bytes):
            raise ValidationError(_('Broker body must be bytes or text.'))
        topic = subscription.topic_id
        if len(body) > topic.max_payload_bytes:
            raise ValidationError(_('Broker payload exceeds the configured size limit.'))
        transport_message_id = transport_message_id or ''
        if topic.message_format == 'raw':
            raw = body.decode('utf-8')
            parsed = raw
        else:
            try:
                parsed = json.loads(body.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ValidationError(_('Broker payload is not valid UTF-8 JSON.')) from error
        if topic.message_format == 'odoo':
            self._validate_internal_envelope(parsed)
            if parsed['topic'] != topic.name:
                raise ValidationError(_('Broker message topic mismatch.'))
            message = dict(parsed)
            message.update({
                'transport_message_id': transport_message_id,
                'physical_topic': _physical_topic(topic),
                '_raw_payload': parsed,
                '_raw_body': body.decode('utf-8'),
                '_payload_size': len(body),
            })
            return message
        try:
            external_id = _path_value(parsed, topic.message_id_path) if topic.message_id_path else None
            event_type = _path_value(parsed, topic.event_type_path) if topic.event_type_path else None
            payload = _path_value(parsed, topic.payload_path) if topic.payload_path else parsed
        except KeyError as error:
            raise ValidationError(_('Required payload path was not found: %s', error.args[0])) from error
        if external_id is not None and isinstance(external_id, (dict, list, bool)):
            raise ValidationError(_('External message ID must be a string or number.'))
        message_id = str(external_id if external_id is not None else transport_message_id or hashlib.sha256(body).hexdigest())
        if len(message_id) > 255:
            raise ValidationError(_('External message ID is too long.'))
        return {
            'id': message_id,
            'version': 1,
            'topic': topic.name,
            'physical_topic': _physical_topic(topic),
            'transport_message_id': transport_message_id,
            'event_type': str(event_type) if event_type is not None else None,
            'record_ids': [],
            'payload': payload,
            '_raw_payload': parsed,
            '_raw_body': body.decode('utf-8'),
            '_payload_size': len(body),
        }

    @api.model
    def _record_rejected(self, subscription, body, transport_message_id, error):
        raw = body.decode('utf-8', 'replace') if isinstance(body, bytes) else str(body)
        message_id = str(transport_message_id or hashlib.sha256(raw.encode()).hexdigest())
        preview = raw[:4096] + ('…' if len(raw) > 4096 else '')
        values = {
            'message_id': message_id[:255],
            'transport_message_id': str(transport_message_id or '')[:255],
            'subscription_id': subscription.id,
            'physical_topic': _physical_topic(subscription.topic_id),
            'state': 'dead',
            'attempt_count': 1,
            'payload': preview if subscription.topic_id.store_payload else False,
            'raw_body': raw if subscription.topic_id.store_payload and len(raw.encode()) <= subscription.topic_id.max_payload_bytes else False,
            'replayable': bool(subscription.topic_id.store_payload and len(raw.encode()) <= subscription.topic_id.max_payload_bytes),
            'payload_size': len(body) if isinstance(body, bytes) else len(raw.encode()),
            'last_attempt_at': fields.Datetime.now(),
            'processed_at': fields.Datetime.now(),
            'last_error': str(error)[:4000],
        }
        existing = self.sudo().search([
            ('message_id', '=', values['message_id']),
            ('subscription_id', '=', subscription.id),
        ], limit=1)
        if existing:
            existing.write({'last_error': values['last_error'], 'attempt_count': existing.attempt_count + 1})
        else:
            self.sudo().create(values)

    @api.model
    def _process_message(self, subscription_id, body, transport_message_id=None):
        subscription = self.env['broker.subscription'].sudo().browse(subscription_id).exists()
        if not subscription or not subscription.active or not subscription.topic_id.active:
            return None
        try:
            message = self._normalize_message(subscription, body, transport_message_id)
        except Exception as error:
            self._record_rejected(subscription, body, transport_message_id, error)
            _logger.warning('Rejected broker message for %s/%s: %s', subscription.topic_id.name, subscription.channel, error)
            # Invalid messages are permanent failures. Recording a dead delivery then ACKing
            # prevents a poison message from occupying NSQ forever.
            return None
        return self._process_normalized(subscription, message)

    @api.model
    def _process(self, subscription_id, envelope):
        """Compatibility entry point for internal envelope callers and tests."""
        subscription = self.env['broker.subscription'].sudo().browse(subscription_id).exists()
        if not subscription or not subscription.active or not subscription.topic_id.active:
            return None
        self._validate_internal_envelope(envelope)
        if envelope['topic'] != subscription.topic_id.name:
            raise ValidationError(_('Broker message topic mismatch.'))
        message = dict(envelope)
        message.setdefault('physical_topic', _physical_topic(subscription.topic_id))
        message.setdefault('transport_message_id', '')
        message.setdefault('_raw_payload', envelope)
        message.setdefault('_raw_body', json.dumps(envelope))
        message.setdefault('_payload_size', len(message['_raw_body'].encode()))
        return self._process_normalized(subscription, message)

    @api.model
    def _process_normalized(self, subscription, message):
        now = fields.Datetime.now()
        stored_payload = message.get('_raw_payload') if subscription.topic_id.store_payload else False
        self.env.cr.execute('''
            INSERT INTO broker_inbox
                (message_id, transport_message_id, subscription_id, physical_topic, event_type,
                 state, attempt_count, payload, raw_body, replayable, payload_size, received_at,
                 create_uid, create_date, write_uid, write_date)
            VALUES (%s, %s, %s, %s, %s, 'processing', 0, %s, %s, %s, %s, %s,
                    %s, NOW() AT TIME ZONE 'UTC', %s, NOW() AT TIME ZONE 'UTC')
            ON CONFLICT (message_id, subscription_id) DO NOTHING
            RETURNING id
        ''', [
            message['id'], message.get('transport_message_id'), subscription.id,
            message.get('physical_topic'), message.get('event_type'),
            json.dumps(stored_payload) if stored_payload is not False else None,
            message.get('_raw_body') if subscription.topic_id.store_payload else None,
            subscription.topic_id.store_payload,
            message.get('_payload_size', 0), now, SUPERUSER_ID, SUPERUSER_ID,
        ])
        created = self.env.cr.fetchone()
        if not created:
            self.env.cr.execute('''
                SELECT id, state FROM broker_inbox
                 WHERE message_id = %s AND subscription_id = %s
                 FOR UPDATE
            ''', [message['id'], subscription.id])
            inbox_id, state = self.env.cr.fetchone()
            if state in ('done', 'skipped', 'processing'):
                return None
        else:
            inbox_id = created[0]
        inbox = self.sudo().browse(inbox_id)
        attempts = inbox.attempt_count + 1
        user = subscription.user_id or self.env.ref('base.user_root')
        context = {'allowed_company_ids': [subscription.company_id.id]} if subscription.company_id else {}
        started = time.monotonic()
        try:
            with self.env.cr.savepoint():
                subscription._execute(self.env(user=user, context=context), message)
        except Exception as error:
            duration = (time.monotonic() - started) * 1000
            max_retries = subscription.topic_id.max_retries
            dead = attempts > max_retries
            inbox.write({
                'state': 'dead' if dead else 'failed',
                'attempt_count': attempts,
                'last_attempt_at': now,
                'duration_ms': duration,
                'last_error': str(error)[:4000],
            })
            if dead:
                if subscription.topic_id.dead_letter_topic:
                    self.env['broker.publisher'].publish(
                        subscription.topic_id.dead_letter_topic,
                        {'message': message.get('_raw_payload'), 'error': str(error)[:1000]},
                    )
                return None
            return subscription.topic_id.retry_delay * attempts
        inbox.write({
            'state': 'done',
            'attempt_count': attempts,
            'last_attempt_at': now,
            'processed_at': fields.Datetime.now(),
            'duration_ms': (time.monotonic() - started) * 1000,
            'last_error': False,
        })
        return None

    def action_requeue(self):
        for delivery in self:
            if delivery.state not in ('failed', 'dead'):
                raise UserError(_('Only failed or dead deliveries can be requeued.'))
            if not delivery.replayable or not delivery.raw_body:
                raise UserError(_('This delivery has no retained transport body and cannot be replayed.'))
            body = delivery.raw_body
            self.env['broker.outbox'].sudo().create({
                'message_id': str(uuid.uuid4()),
                'topic_id': delivery.topic_id.id,
                'user_id': self.env.uid,
                'company_id': self.env.company.id,
                'record_ids': [],
                'payload': {},
                'body_override': body,
            })
        return True

    @api.autovacuum
    def _gc_done(self):
        # ponytail: fixed retention keeps config small; add per-topic retention when operations require it.
        cutoff = fields.Datetime.now() - timedelta(days=30)
        self.search([('state', 'in', ('done', 'skipped')), ('processed_at', '<', cutoff)]).unlink()
