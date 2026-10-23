# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.broker.api import handler
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

_HANDLER_CALLS = []


@handler('base.test.handler.v1')
def _test_handler(env, message):
    _HANDLER_CALLS.append(message['id'])


class TestBroker(TransactionCase):

    def setUp(self):
        super().setUp()
        _HANDLER_CALLS.clear()
        self.topic = self.env['broker.topic'].create({'name': 'base.test.handler.v1'})

    def test_transactional_publish(self):
        message_id = self.env['broker.publisher'].publish(
            self.topic.name, {'value': 42}, record_ids=[1, 2]
        )
        outbox = self.env['broker.outbox'].search([('message_id', '=', message_id)])
        self.assertEqual(outbox.state, 'pending')
        self.assertEqual(outbox.record_ids, [1, 2])
        self.assertEqual(outbox._envelope()['database'], self.env.cr.dbname)

    def test_invalid_payload(self):
        with self.assertRaises(ValidationError):
            self.env['broker.publisher'].publish(self.topic.name, ['not', 'an', 'object'])
        with self.assertRaises(ValidationError):
            self.env['broker.publisher'].publish(self.topic.name, {}, record_ids=[True])

    def test_idempotent_consume(self):
        subscription = self.env['broker.subscription'].create({
            'topic_id': self.topic.id,
            'channel': 'test',
            'handler': self.topic.name,
        })
        message_id = self.env['broker.publisher'].publish(self.topic.name, {})
        outbox = self.env['broker.outbox'].search([('message_id', '=', message_id)])
        envelope = outbox._envelope()
        self.assertIsNone(self.env['broker.inbox']._process(subscription.id, envelope))
        self.assertIsNone(self.env['broker.inbox']._process(subscription.id, envelope))
        self.assertEqual(_HANDLER_CALLS, [message_id])

    def test_external_json_consume_and_deduplicate(self):
        topic = self.env['broker.topic'].create({
            'name': 'external.orders.v1',
            'ownership': 'external',
            'direction': 'inbound',
            'physical_name_mode': 'exact',
            'physical_topic': 'partner.orders.v1',
            'message_format': 'json',
            'message_id_path': 'event.id',
            'event_type_path': 'event.type',
            'payload_path': 'data',
        })
        subscription = self.env['broker.subscription'].create({
            'topic_id': topic.id,
            'channel': 'odoo-orders',
            'handler': self.topic.name,
        })
        body = b'{"event":{"id":"evt-42","type":"order.created"},"data":{"order":"SO42"}}'
        self.assertIsNone(self.env['broker.inbox']._process_message(subscription.id, body, 'nsq-1'))
        self.assertIsNone(self.env['broker.inbox']._process_message(subscription.id, body, 'nsq-2'))
        delivery = self.env['broker.inbox'].search([('subscription_id', '=', subscription.id)])
        self.assertEqual(len(delivery), 1)
        self.assertEqual(delivery.message_id, 'evt-42')
        self.assertEqual(delivery.event_type, 'order.created')
        self.assertEqual(delivery.payload['data']['order'], 'SO42')
        self.assertIn('"order": "SO42"', delivery.payload_display)
        self.assertEqual(_HANDLER_CALLS, ['evt-42'])

    def test_python_channel(self):
        topic = self.env['broker.topic'].create({
            'name': 'external.python.v1',
            'ownership': 'external',
            'direction': 'inbound',
            'message_format': 'json',
            'message_id_path': 'id',
        })
        subscription = self.env['broker.subscription'].create({
            'topic_id': topic.id,
            'channel': 'python',
            'handler_type': 'code',
            'model_id': self.env['ir.model']._get_id('res.partner'),
            'code': "log('received %s' % payload['id'])",
        })
        delay = self.env['broker.inbox']._process_message(subscription.id, b'{"id":"evt-code"}')
        delivery = self.env['broker.inbox'].search([('subscription_id', '=', subscription.id)])
        self.assertIsNone(delay, delivery.last_error)
        self.assertEqual(delivery.state, 'done')

    def test_broker_display_names_include_context(self):
        subscription = self.env['broker.subscription'].create({
            'topic_id': self.topic.id,
            'channel': 'display-name',
            'handler': self.topic.name,
        })
        message_id = self.env['broker.publisher'].publish(self.topic.name, {})
        outbox = self.env['broker.outbox'].search([('message_id', '=', message_id)])
        self.env['broker.inbox']._process(subscription.id, outbox._envelope())
        delivery = self.env['broker.inbox'].search([('subscription_id', '=', subscription.id)])
        self.assertEqual(self.topic.display_name, f'{self.topic.name} [{self.topic.physical_topic_display}]')
        self.assertEqual(subscription.display_name, f'{self.topic.name} / display-name')
        self.assertEqual(outbox.display_name, f'{self.topic.name} / {message_id}')
        self.assertEqual(delivery.display_name, f'{self.topic.name} / display-name / {message_id}')

    def test_external_invalid_json_is_visible_dead_letter(self):
        topic = self.env['broker.topic'].create({
            'name': 'external.invalid.v1',
            'ownership': 'external',
            'direction': 'inbound',
            'message_format': 'json',
        })
        subscription = self.env['broker.subscription'].create({
            'topic_id': topic.id,
            'channel': 'invalid',
            'handler': self.topic.name,
        })
        self.assertIsNone(self.env['broker.inbox']._process_message(subscription.id, b'not-json', 'nsq-invalid'))
        delivery = self.env['broker.inbox'].search([('subscription_id', '=', subscription.id)])
        self.assertEqual(delivery.state, 'dead')
        self.assertIn('not valid', delivery.last_error)
        delivery.action_requeue()
        replay = self.env['broker.outbox'].search([('topic_id', '=', topic.id)])
        self.assertEqual(replay.body_override, 'not-json')
