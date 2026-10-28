# Part of Odoo. See LICENSE file for full copyright and licensing details.
from types import SimpleNamespace
from unittest.mock import patch

from odoo import http
from odoo.tools import config
from odoo.tests.common import BaseCase


class TestHttpPerformance(BaseCase):
    def test_deterministic_sampling(self):
        with patch.object(http, '_performance_sample_credit', 0.0):
            self.assertEqual([http._sample_request(0.25) for _index in range(8)], [
                False, False, False, True, False, False, False, True,
            ])

    def test_performance_instrumentation_disabled_by_default(self):
        self.assertEqual(config['log_performance_sample_rate'], 0.0)
        self.assertEqual(config['log_performance_slow_ms'], 0)

    def test_unsampled_request_uses_fast_path(self):
        with patch.object(config, 'options', {
            **config.options,
            'log_performance_sample_rate': 0.01,
            'log_performance_slow_ms': 0,
        }), patch.object(http, '_sample_request', return_value=False):
            self.assertEqual(http._start_request_performance(), (False, None, None))

    def test_slow_request_threshold_times_without_detailed_metrics(self):
        with patch.object(config, 'options', {
            **config.options,
            'log_performance_sample_rate': 0.0,
            'log_performance_slow_ms': 500,
        }), patch.object(http, '_sample_request', return_value=False):
            sampled, metrics, started = http._start_request_performance()
        self.assertFalse(sampled)
        self.assertIsNone(metrics)
        self.assertIsInstance(started, float)

    def test_disabled_logger_uses_fast_path(self):
        with patch.object(http._performance_logger, 'isEnabledFor', return_value=False):
            self.assertEqual(http._start_request_performance(), (False, None, None))

    def test_admission_control_disabled_uses_fast_path(self):
        with patch.object(config, 'options', {**config.options, 'http_max_inflight': 0}), \
             patch.object(http, '_inflight_lock') as lock:
            self.assertIsNone(http._try_enter_request())
        lock.__enter__.assert_not_called()

    def test_admission_control(self):
        with patch.object(config, 'options', {**config.options, 'http_max_inflight': 1}), \
             patch.object(http, '_inflight_requests', 0):
            self.assertTrue(http._try_enter_request())
            self.assertFalse(http._try_enter_request())
            http._leave_request()
            self.assertTrue(http._try_enter_request())
            http._leave_request()

    def test_performance_log_contains_no_query_or_payload(self):
        request = SimpleNamespace(httprequest=SimpleNamespace(method='POST', path='/web/dataset/call_kw'))
        response = SimpleNamespace(status_code=200, content_length=42)
        with patch.object(config, 'options', {
            **config.options,
            'log_performance_sample_rate': 1.0,
            'log_performance_slow_ms': 0,
            'db_maxconn': 64,
        }), patch.object(http.odoo.sql_db, 'connection_pool_stats', return_value={
            'used': 1, 'count': 2, 'max': 64,
        }), patch.object(http._performance_logger, 'info') as info:
            http._log_request_performance(request, response, http.time.perf_counter(), sampled=True)

        message, *values = info.call_args.args
        self.assertIn('path=%s', message)
        self.assertIn('response_bytes=%s', message)
        self.assertNotIn('query=', message)
        self.assertNotIn('payload=', message)
        self.assertEqual(values[1], '/web/dataset/call_kw')
        self.assertEqual(values[-1], 42)
