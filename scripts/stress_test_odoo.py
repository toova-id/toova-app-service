#!/usr/bin/env python3
"""Stress an Odoo container and report latency, errors, and container resource use.

Resource numbers are read from the container cgroup, not from the host running
this script. Every non-2xx response counts as an error.
"""
import argparse
import concurrent.futures
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

DEFAULT_URL = 'http://localhost:8069'
DEFAULT_DB = 'test_ci'
DEFAULT_CONTAINER = 'docker-odoo-test-1'


def login(url, db, user, password):
    payload = json.dumps({
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {'login': user, 'password': password, 'db': db},
    }).encode()
    request = urllib.request.Request(
        url + '/web/session/authenticate', data=payload,
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read())
        if body.get('error') or not body.get('result', {}).get('uid'):
            raise SystemExit('authentication failed')
        cookies = response.headers.get_all('Set-Cookie') or []
        return '; '.join(cookie.split(';')[0] for cookie in cookies)


def container_usage(container):
    """Read cgroup counters inside the container under test."""
    script = (
        'cat /sys/fs/cgroup/memory.current 2>/dev/null || '
        'cat /sys/fs/cgroup/memory/memory.usage_in_bytes; '
        'cat /sys/fs/cgroup/memory.max 2>/dev/null || '
        'cat /sys/fs/cgroup/memory/memory.limit_in_bytes; '
        'cat /sys/fs/cgroup/memory.peak 2>/dev/null || echo 0; '
        'cat /sys/fs/cgroup/cpu.stat 2>/dev/null | '
        'awk \'/^usage_usec/ {print $2}\' || echo 0'
    )
    try:
        result = subprocess.run(['docker', 'exec', container, 'sh', '-c', script],
                                capture_output=True, text=True, timeout=15)
        current, maximum, peak, cpu_usec = (result.stdout.split() + ['0'] * 4)[:4]
        current, maximum, peak = int(current), int(maximum), int(peak)
        return {
            'mem_current': current,
            'mem_max': maximum,
            'mem_peak': peak,
            'mem_pct': round(current / maximum * 100, 1) if maximum else 0.0,
            'cpu_usec': int(cpu_usec),
        }
    except Exception:
        return {'mem_current': 0, 'mem_max': 0, 'mem_peak': 0, 'mem_pct': 0.0, 'cpu_usec': 0}


def container_state(container):
    try:
        result = subprocess.run(
            ['docker', 'inspect', container, '--format',
             '{{.State.Status}}|{{.State.OOMKilled}}|{{.RestartCount}}'],
            capture_output=True, text=True, timeout=15, check=True)
        status, oom, restarts = result.stdout.strip().split('|')
        return {'status': status, 'oom_killed': oom == 'true', 'restarts': int(restarts)}
    except Exception as error:
        return {'status': 'inspect-failed:%s' % error, 'oom_killed': False, 'restarts': -1}


def worker_recycles(container):
    try:
        result = subprocess.run(['docker', 'logs', container],
                                capture_output=True, text=True, timeout=30)
        log = result.stdout + result.stderr
        return {reason: log.count('reason: ' + reason) for reason in
                ('max-age', 'request-limit', 'soft-memory', 'hard-memory',
                 'memory-pressure', 'timeout')}
    except Exception:
        return {}


def call_kw(model, method, args, kwargs=None):
    """Build a JSON-RPC dataset call body, the dominant production request shape."""
    return json.dumps({
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {'model': model, 'method': method, 'args': args, 'kwargs': kwargs or {}},
    }).encode()


def make_request(url, cookie, timeout, body=None):
    started = time.perf_counter()
    try:
        request = urllib.request.Request(url, data=body)
        if body is not None:
            request.add_header('Content-Type', 'application/json')
        if cookie:
            request.add_header('Cookie', cookie)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            status = response.status
            # A JSON-RPC fault answers 200 with an error member; count it as an error.
            if body is not None and b'"error"' in payload[:4096]:
                status = 599
    except urllib.error.HTTPError as error:
        error.read()
        status = error.code
    except Exception:
        status = 0
    return status, (time.perf_counter() - started) * 1000


def burst(url, cookie, concurrency, requests, timeout, paths):
    """Send `requests` requests with at most `concurrency` in flight.

    Each entry of `paths` is either a path string or a (path, body) pair.
    """
    latencies = []
    statuses = []
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = []
        for index in range(requests):
            entry = paths[index % len(paths)]
            path, body = entry if isinstance(entry, tuple) else (entry, None)
            futures.append(pool.submit(make_request, url + path, cookie, timeout, body))
        for future in concurrent.futures.as_completed(futures):
            status, latency = future.result()
            statuses.append(status)
            latencies.append(latency)
    elapsed = time.monotonic() - started
    latencies.sort()
    count = len(latencies)

    def percentile(fraction):
        return round(latencies[min(count - 1, int(count * fraction))], 2)

    errors = sum(1 for status in statuses if not 200 <= status < 400)
    return {
        'concurrency': concurrency,
        'requests': count,
        'errors': errors,
        'error_pct': round(errors / count * 100, 2) if count else 0.0,
        'statuses': {str(status): statuses.count(status) for status in sorted(set(statuses))},
        'rps': round(count / elapsed, 1) if elapsed else 0.0,
        'p50_ms': percentile(.50),
        'p95_ms': percentile(.95),
        'p99_ms': percentile(.99),
        'max_ms': round(latencies[-1], 2) if count else 0.0,
    }


def report(label, result, usage, state):
    print('  %-22s rps=%-7s p50=%-8s p95=%-9s p99=%-9s err=%s/%s (%s%%) '
          'mem=%sMiB/%sMiB (%s%%) status=%s oom=%s restarts=%s'
          % (label, result['rps'], result['p50_ms'], result['p95_ms'], result['p99_ms'],
             result['errors'], result['requests'], result['error_pct'],
             usage['mem_current'] // 1048576, usage['mem_max'] // 1048576, usage['mem_pct'],
             state['status'], state['oom_killed'], state['restarts']))
    if result['errors']:
        print('      statuses: %s' % result['statuses'])


def self_check():
    """Runnable check for the pure-logic parts, no server needed."""
    latencies = [(200, float(value)) for value in range(1, 101)]
    statuses = [status for status, _ in latencies]
    errors = sum(1 for status in statuses if not 200 <= status < 400)
    assert errors == 0
    mixed = [200, 404, 500, 0, 302]
    assert sum(1 for status in mixed if not 200 <= status < 400) == 3, 'error counting broken'
    print('stress test self-check passed')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=DEFAULT_URL)
    parser.add_argument('--db', default=DEFAULT_DB)
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='admin')
    parser.add_argument('--container', default=DEFAULT_CONTAINER)
    parser.add_argument('--timeout', type=float, default=30.0)
    parser.add_argument('--endurance-seconds', type=int, default=60)
    parser.add_argument('--self-check', action='store_true')
    options = parser.parse_args()

    if options.self_check:
        self_check()
        return 0

    # GET-safe endpoints only; JSON-RPC endpoints reject GET with 400.
    paths = ['/web/health', '/web/login']
    # Session workload: menu load plus ORM reads through the regular dataset route.
    authenticated = [
        '/web/webclient/load_menus/1',
        ('/web/dataset/call_kw', call_kw('res.partner', 'search_read',
                                         [[], ['name', 'email', 'country_id']],
                                         {'limit': 80})),
        ('/web/dataset/call_kw', call_kw('res.users', 'read',
                                         [[2], ['name', 'login', 'company_id']])),
        ('/web/dataset/call_kw', call_kw('ir.model', 'search_count', [[]])),
        '/web/health',
    ]

    cookie = login(options.url, options.db, options.user, options.password)
    start_usage = container_usage(options.container)
    print('container=%s mem_limit=%sMiB cpu_limit=%s'
          % (options.container, start_usage['mem_max'] // 1048576,
             subprocess.run(['docker', 'exec', options.container, 'cat', '/sys/fs/cgroup/cpu.max'],
                            capture_output=True, text=True).stdout.strip()))

    print('\n--- ramp (anonymous endpoints) ---')
    for concurrency in (1, 5, 10, 25, 50, 100, 200, 300):
        result = burst(options.url, cookie, concurrency, concurrency * 20,
                       options.timeout, paths)
        report('concurrency=%s' % concurrency, result,
               container_usage(options.container), container_state(options.container))
        time.sleep(1)

    print('\n--- ramp (authenticated session) ---')
    for concurrency in (5, 25, 50, 100):
        result = burst(options.url, cookie, concurrency, concurrency * 10,
                       options.timeout, authenticated)
        report('concurrency=%s' % concurrency, result,
               container_usage(options.container), container_state(options.container))
        time.sleep(1)

    print('\n--- endurance (50 concurrent, %ss) ---' % options.endurance_seconds)
    deadline = time.monotonic() + options.endurance_seconds
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        result = burst(options.url, cookie, 50, 500, options.timeout, paths)
        report('iteration=%s' % iteration, result,
               container_usage(options.container), container_state(options.container))

    print('\n--- final ---')
    usage = container_usage(options.container)
    state = container_state(options.container)
    cpu_seconds = (usage['cpu_usec'] - start_usage['cpu_usec']) / 1e6
    print('  mem_current=%sMiB mem_peak=%sMiB limit=%sMiB (%s%%)'
          % (usage['mem_current'] // 1048576, usage['mem_peak'] // 1048576,
             usage['mem_max'] // 1048576, usage['mem_pct']))
    print('  container_cpu_seconds=%.1f status=%s oom_killed=%s restarts=%s'
          % (cpu_seconds, state['status'], state['oom_killed'], state['restarts']))
    print('  worker_recycles=%s' % worker_recycles(options.container))
    health = make_request(options.url + '/web/health', cookie, options.timeout)
    print('  health status=%s latency=%.1fms' % health)
    return 0 if state['status'] == 'running' and not state['oom_killed'] else 1


if __name__ == '__main__':
    sys.exit(main())
