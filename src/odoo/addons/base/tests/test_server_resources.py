# Part of Odoo. See LICENSE file for full copyright and licensing details.
from types import SimpleNamespace
from unittest.mock import patch

from odoo.service import server
from odoo.tests.common import BaseCase
from odoo.tools import config


class TestServerResources(BaseCase):
    def test_cgroup_v2(self):
        values = iter(("157286400", "2306867200", "94000 100000", None, None,
                       "usage_usec 4\nthrottled_usec 7"))
        with patch.object(server, '_read_first', side_effect=lambda paths: next(values)):
            self.assertEqual(server.cgroup_info(), {
                'memory_current': 157286400,
                'memory_max': 2306867200,
                'cpu_quota': 94000,
                'cpu_period': 100000,
                'cpu_throttled_usec': 7,
            })

    def test_cgroup_v1(self):
        values = iter(("157286400", "2306867200", None, "94000", "100000", "throttled_time 7000"))
        with patch.object(server, '_read_first', side_effect=lambda paths: next(values)):
            self.assertEqual(server.cgroup_info(), {
                'memory_current': 157286400,
                'memory_max': 2306867200,
                'cpu_quota': 94000,
                'cpu_period': 100000,
                'cpu_throttled_usec': 7,
            })

    def test_cgroup_memory_pressure(self):
        with patch.object(config, 'options', {
            **config.options, 'limit_memory_pressure': 0.9,
        }), patch.object(server, '_read_first', side_effect=('91', '100')):
            self.assertTrue(server.cgroup_memory_pressure_reached())

    def test_cgroup_memory_pressure_disabled(self):
        with patch.object(config, 'options', {
            **config.options, 'limit_memory_pressure': 0.0,
        }), patch.object(server, '_read_first') as read_first:
            self.assertFalse(server.cgroup_memory_pressure_reached())
        read_first.assert_not_called()

    def test_process_memory_info(self):
        process = SimpleNamespace(
            memory_info=lambda: SimpleNamespace(rss=1, vms=2),
            memory_full_info=lambda: SimpleNamespace(pss=3, uss=4),
        )
        self.assertEqual(server.process_memory_info(process), {
            'rss': 1,
            'vms': 2,
            'pss': 3,
            'uss': 4,
        })
        for metric, expected in [('vms', 2), ('rss', 1), ('pss', 3), ('uss', 4)]:
            with patch.object(config, 'options', {**config.options, 'limit_memory_metric': metric}):
                self.assertEqual(server.memory_info(process), expected)

    def test_http_worker_age_jitter_uses_generation_offset(self):
        multi = SimpleNamespace(pipe_new=lambda: (1, 2), timeout=120, limit_request=1000,
                                generation=20)
        with patch.object(config, 'options', {
            **config.options,
            'limit_time_worker': 100,
            'limit_time_worker_jitter': 20,
            'limit_request_jitter': 0,
        }):
            worker = server.WorkerHTTP(multi)
        self.assertEqual(worker.max_age, 120)

    def test_server_wide_modules_follow_runtime_role(self):
        cases = {
            'http': ['custom', 'web', 'base'],
            'realtime': ['custom', 'base', 'bus'],
            'cron': ['custom', 'base'],
            'broker': ['custom', 'base'],
            'all': ['custom', 'web', 'base'],
        }
        for role, expected in cases.items():
            with self.subTest(role=role), patch.object(config, 'options', {
                **config.options, 'runtime_role': role,
            }), patch.object(server.odoo.conf, 'server_wide_modules', ['custom', 'web']):
                self.assertEqual(server.server_wide_modules_for_role(), expected)

    def test_http_role_does_not_spawn_realtime(self):
        prefork = object.__new__(server.PreforkServer)
        prefork.population = 1
        prefork.spawn_paused = False
        prefork.workers = {}
        prefork.workers_http = {42: object()}
        prefork.workers_cron = {}
        prefork.long_polling_pid = None
        with patch.object(config, 'options', {
            **config.options,
            'runtime_role': 'http',
            'http_enable': True,
            'max_cron_threads': 0,
        }), patch.object(server, 'cgroup_memory_pressure_reached', return_value=False), \
             patch.object(prefork, 'long_polling_spawn') as long_polling_spawn:
            prefork.process_spawn()
        long_polling_spawn.assert_not_called()

    def test_all_role_spawns_realtime(self):
        prefork = object.__new__(server.PreforkServer)
        prefork.population = 1
        prefork.spawn_paused = False
        prefork.workers = {}
        prefork.workers_http = {42: object()}
        prefork.workers_cron = {}
        prefork.long_polling_pid = None
        with patch.object(config, 'options', {
            **config.options,
            'runtime_role': 'all',
            'http_enable': True,
            'max_cron_threads': 0,
        }), patch.object(server, 'cgroup_memory_pressure_reached', return_value=False), \
             patch.object(prefork, 'long_polling_spawn') as long_polling_spawn:
            prefork.process_spawn()
        long_polling_spawn.assert_called_once_with()

    def test_cron_health_touch(self):
        worker = object.__new__(server.WorkerCron)
        worker.health_file = '/tmp/cron-health-test'
        with patch('builtins.open') as health, patch.object(server.os, 'utime') as utime:
            worker._touch_health()
        health.assert_called_once_with('/tmp/cron-health-test', 'a')
        utime.assert_called_once_with('/tmp/cron-health-test')

    def test_prefork_hard_memory_watchdog(self):
        prefork = object.__new__(server.PreforkServer)
        worker = SimpleNamespace(watchdog_timeout=None, recycle_reason=None)
        prefork.workers = {42: worker}
        with patch.object(config, 'options', {
            **config.options,
            'limit_memory_hard': 100,
            'limit_memory_metric': 'rss',
        }), patch.object(server.psutil, 'Process', return_value=SimpleNamespace(
            memory_info=lambda: SimpleNamespace(rss=101, vms=1000),
        )), patch.object(prefork, 'worker_kill') as worker_kill:
            prefork.process_timeout()
        self.assertEqual(worker.recycle_reason, 'hard-memory')
        worker_kill.assert_called_once_with(42, server.signal.SIGKILL)

    def test_prefork_retires_largest_http_worker_under_pressure(self):
        prefork = object.__new__(server.PreforkServer)
        small = SimpleNamespace(recycle_reason=None)
        large = SimpleNamespace(recycle_reason=None)
        prefork.workers_http = {41: small, 42: large}
        with patch.object(server.psutil, 'Process', side_effect=lambda pid: SimpleNamespace(
            memory_info=lambda: SimpleNamespace(rss=pid, vms=pid),
        )), patch.object(config, 'options', {
            **config.options, 'limit_memory_metric': 'rss',
        }), patch.object(prefork, 'worker_kill') as worker_kill:
            prefork.retire_worker_under_memory_pressure()
        self.assertIsNone(small.recycle_reason)
        self.assertEqual(large.recycle_reason, 'memory-pressure')
        worker_kill.assert_called_once_with(42, server.signal.SIGINT)

    def test_prefork_keeps_one_http_worker_under_pressure(self):
        prefork = object.__new__(server.PreforkServer)
        worker = SimpleNamespace(recycle_reason=None)
        prefork.workers_http = {42: worker}
        with patch.object(prefork, 'worker_kill') as worker_kill:
            prefork.retire_worker_under_memory_pressure()
        self.assertIsNone(worker.recycle_reason)
        worker_kill.assert_not_called()

    def test_prefork_hard_memory_watchdog_does_not_kill_twice(self):
        prefork = object.__new__(server.PreforkServer)
        prefork.workers = {42: SimpleNamespace(
            watchdog_timeout=None, recycle_reason='hard-memory',
        )}
        with patch.object(config, 'options', {
            **config.options,
            'limit_memory_hard': 100,
            'limit_memory_metric': 'rss',
        }), patch.object(prefork, 'worker_kill') as worker_kill:
            prefork.process_timeout()
        worker_kill.assert_not_called()
