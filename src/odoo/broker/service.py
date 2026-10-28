# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import signal
import threading
import time

import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry
from odoo.service.server import CommonServer, preload_registries
from odoo.tools import config
from .providers import get_provider

_logger = logging.getLogger(__name__)


class BrokerServer(CommonServer):
    """Isolated ORM-capable message broker runtime."""

    def __init__(self, app=None):
        super().__init__(app)
        self.alive = True
        self.provider = get_provider(config)
        configured_databases = config['broker_database'] or config['db_name'] or ''
        if isinstance(configured_databases, (list, tuple)):
            db_names = [name for name in configured_databases if name]
        else:
            db_names = [name for name in configured_databases.split(',') if name]
        if len(db_names) != 1:
            raise ValueError('runtime_role=broker requires exactly one broker database')
        self.db_name = db_names[0]
        self.relay_thread = None
        self.consumer_thread = None
        self.relay_heartbeat = 0.0
        self.health_file = '/tmp/odoo-broker-health'

    def signal_handler(self, sig, frame):
        self.alive = False
        self.provider.stop()

    def _relay(self):
        claimed_ids = set()
        while self.alive:
            try:
                with Registry(self.db_name).cursor() as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    batch = env['broker.outbox']._claim_batch(config['broker_batch_size'])
                    cr.commit()
                claimed_ids.update(item['id'] for item in batch)
                for item in batch:
                    try:
                        self.provider.publish(item['physical_topic'], item['body'].encode())
                        with Registry(self.db_name).cursor() as success_cr:
                            success_env = api.Environment(success_cr, SUPERUSER_ID, {})
                            success_env['broker.outbox']._mark_published(item['id'])
                            success_cr.commit()
                        claimed_ids.discard(item['id'])
                    except Exception as error:
                        with Registry(self.db_name).cursor() as error_cr:
                            error_env = api.Environment(error_cr, SUPERUSER_ID, {})
                            error_env['broker.outbox']._mark_failed(item['id'], str(error))
                            error_cr.commit()
                        claimed_ids.discard(item['id'])
                        _logger.warning('Broker publish failed for outbox %s.', item['id'], exc_info=True)
            except Exception:
                _logger.exception('Broker outbox relay failed.')
            finally:
                self.relay_heartbeat = time.monotonic()
            if self.alive:
                time.sleep(config['broker_poll_seconds'])
        # Claimed but unpublished rows recover immediately on graceful shutdown.
        if claimed_ids:
            with Registry(self.db_name).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['broker.outbox'].browse(list(claimed_ids)).write({'state': 'pending'})
                cr.commit()

    def _subscriptions(self):
        with Registry(self.db_name).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            result = env['broker.subscription']._runtime_definitions()
            cr.commit()
            return result

    def _run_consumer(self, subscriptions):
        try:
            self.provider.consume(subscriptions, self._consume)
        except Exception:
            _logger.exception('Broker consumer stopped unexpectedly.')
            self.alive = False

    def _healthy(self):
        heartbeat_timeout = max(30, config['broker_poll_seconds'] * 5)
        relay_healthy = (
            self.relay_thread is not None and self.relay_thread.is_alive() and
            time.monotonic() - self.relay_heartbeat <= heartbeat_timeout
        )
        consumer_healthy = self.consumer_thread is None or self.consumer_thread.is_alive()
        return relay_healthy, consumer_healthy

    def _consume(self, subscription, message):
        try:
            transport_message_id = getattr(message, 'id', b'')
            if isinstance(transport_message_id, bytes):
                transport_message_id = transport_message_id.decode('ascii', 'replace')
            with Registry(self.db_name).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                delay = env['broker.inbox']._process_message(
                    subscription['id'], message.body, transport_message_id,
                )
                cr.commit()
            if delay is None:
                message.finish()
            else:
                message.requeue(delay=delay, backoff=False)
        except Exception:
            _logger.exception('Broker consumer failed before retry policy could run.')
            message.requeue(delay=60, backoff=False)
        return True

    def run(self, preload=None, stop=False):
        rc = preload_registries(preload or [self.db_name])
        if stop or rc:
            return rc
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        self.relay_heartbeat = time.monotonic()
        self.relay_thread = threading.Thread(target=self._relay, name='odoo.broker.relay', daemon=True)
        self.relay_thread.start()
        subscriptions = self._subscriptions()
        if not subscriptions:
            _logger.warning('No enabled broker subscriptions; running outbox relay only.')
        else:
            # pynsq owns Tornado's main thread; run it separately so the relay
            # remains active even before any client subscription is configured.
            self.consumer_thread = threading.Thread(
                target=self._run_consumer, args=(subscriptions,),
                name='odoo.broker.consumer', daemon=True,
            )
            self.consumer_thread.start()
        while self.alive:
            relay_healthy, consumer_healthy = self._healthy()
            if relay_healthy and consumer_healthy:
                with open(self.health_file, 'a'):
                    os.utime(self.health_file)
            else:
                try:
                    os.unlink(self.health_file)
                except FileNotFoundError:
                    pass
                _logger.error('Broker runtime unhealthy: relay=%s consumer=%s.', relay_healthy, consumer_healthy)
                self.alive = False
            time.sleep(1)
        self.stop()
        return 0

    def stop(self):
        self.alive = False
        try:
            os.unlink(self.health_file)
        except FileNotFoundError:
            pass
        self.provider.stop()
        current_thread = threading.current_thread()
        if self.relay_thread and self.relay_thread is not current_thread:
            self.relay_thread.join(timeout=5)
        if self.consumer_thread and self.consumer_thread is not current_thread:
            self.consumer_thread.join(timeout=5)
        super().stop()
