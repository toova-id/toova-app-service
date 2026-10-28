# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from unittest.mock import MagicMock, patch

from odoo.modules import registry
from odoo.tests.common import BaseCase


class TestRegistrySignaling(BaseCase):
    def setUp(self):
        super().setUp()
        with registry._signal_state_lock:
            registry._signal_state.clear()

    def test_state_updates_each_generation_independently_and_monotonically(self):
        self.assertEqual(registry.update_signaling_state('db', 4, 7), (4, 7))
        self.assertEqual(registry.update_signaling_state('db', 3, 8), (4, 8))
        self.assertEqual(registry.get_signaling_state('db'), (4, 8))

    def test_reconciliation_can_replace_state_after_database_restore(self):
        registry.update_signaling_state('db', 10, 12)
        self.assertEqual(registry.reconcile_signaling_state('db', 2, 3), (2, 3))

    def test_listener_consumes_generation_payload(self):
        listener = registry.SignalingListener('db')
        self.assertFalse(listener.consume(json.dumps({'db': 'db', 'registry': 5})))
        self.assertFalse(listener.consume(json.dumps({'db': 'db', 'cache': 9})))
        self.assertEqual(registry.get_signaling_state('db'), (5, 9))

    def test_listener_reconciles_generation_gap(self):
        listener = registry.SignalingListener('db')
        registry.update_signaling_state('db', 4, 7)
        self.assertTrue(listener.consume(json.dumps({'db': 'db', 'registry': 6})))
        self.assertEqual(registry.get_signaling_state('db'), (6, 7))

    def test_listener_reconcile_uses_supplied_connection(self):
        listener = registry.SignalingListener('db')
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (11, 13)

        listener.reconcile(connection)

        cursor.execute.assert_called_once_with(registry._SIGNALING_SEQUENCES_SQL)
        self.assertEqual(registry.get_signaling_state('db'), (11, 13))

    def test_unfreeze_preload_heap_runs_once(self):
        with patch.object(registry, '_preload_heap_frozen', True), \
             patch.object(registry.gc, 'unfreeze') as unfreeze:
            self.assertTrue(registry.unfreeze_preload_heap())
            self.assertFalse(registry.unfreeze_preload_heap())
        unfreeze.assert_called_once()

    def test_started_listener_uses_lock_free_fast_path(self):
        listener = registry.SignalingListener('db')
        listener.pid = registry.os.getpid()
        listener.thread = MagicMock()
        listener.thread.is_alive.return_value = True
        with patch.dict(registry._signal_listeners, {'db': listener}, clear=True), \
             patch.object(registry, '_signal_listener_lock') as lock:
            self.assertIs(registry.start_signaling_listener('db'), listener)
        lock.__enter__.assert_not_called()

    def test_listener_ignores_other_database_payload(self):
        listener = registry.SignalingListener('db')
        with patch.object(registry._logger, 'warning') as warning:
            listener.consume(json.dumps({'db': 'other', 'registry': 5}))
        self.assertEqual(registry.get_signaling_state('db'), (None, None))
        warning.assert_called_once()

    def test_invalid_payload_does_not_mutate_state(self):
        listener = registry.SignalingListener('db')
        with patch.object(registry._logger, 'warning') as warning:
            listener.consume('not-json')
        self.assertEqual(registry.get_signaling_state('db'), (None, None))
        warning.assert_called_once()
