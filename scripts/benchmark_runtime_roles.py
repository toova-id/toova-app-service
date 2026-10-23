#!/usr/bin/env python3
"""Benchmark isolated Odoo HTTP, cron, and broker roles with Docker limits."""
import argparse
import concurrent.futures
import json
import math
import random
import subprocess
import time
import urllib.request


def sh(*args, input=None, check=True):
    return subprocess.run(args, input=input, text=True, capture_output=True, check=check)


def docker(*args, **kwargs):
    return sh('docker', *args, **kwargs)


def usage(container):
    code = "cat /sys/fs/cgroup/memory.current; cat /sys/fs/cgroup/memory.peak; awk '/^usage_usec/ {print $2}' /sys/fs/cgroup/cpu.stat"
    values = docker('exec', container, 'sh', '-c', code).stdout.split()
    return tuple(map(int, values))


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, math.ceil(len(values) * p) - 1)]


def rpc(url, cookie, model, method, args, kwargs=None, timeout=30):
    body = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': {
        'model': model, 'method': method, 'args': args, 'kwargs': kwargs or {},
    }}).encode()
    request = urllib.request.Request(url + '/web/dataset/call_kw', body, {
        'Content-Type': 'application/json', 'Cookie': cookie,
    })
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read())
            ok = response.status == 200 and 'error' not in result
    except Exception:
        ok = False
    return ok, (time.perf_counter() - started) * 1000


def login(url):
    body = json.dumps({'jsonrpc': '2.0', 'method': 'call', 'params': {
        'db': 'bench_roles', 'login': 'admin', 'password': 'admin',
    }}).encode()
    request = urllib.request.Request(url + '/web/session/authenticate', body, {'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        assert json.loads(response.read())['result']['uid']
        return response.headers['Set-Cookie'].split(';', 1)[0]


def wait_http(url, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url + '/web/health', timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(.25)
    raise RuntimeError('HTTP readiness timeout')


def shell(image, network, script):
    result = docker('run', '--rm', '--network', network, '--entrypoint', '/bin/sh', image, '-c',
        "printf '%s\\n' " + ' '.join(json.dumps(line) for line in script.splitlines()) +
        " | /opt/odoo/odoo-bin shell --db_host=db --db_user=odoo --db_password=odoo -d bench_roles --no-http --log-level=error")
    return result.stdout


def start(name, image, network, cpus, memory, *args, ports=()):
    docker('rm', '-f', name, check=False)
    command = ['run', '-d', '--name', name, '--network', network, '--cpus', str(cpus), '--memory', memory]
    if name == 'odoo-bench-cron':
        command += ['-e', 'ODOO_NOTIFY_CRON_CHANGES=1']
    for port in ports:
        command += ['-p', port]
    command += ['--entrypoint', '/opt/odoo/odoo-bin', image,
        '--db_host=db', '--db_user=odoo', '--db_password=odoo', '-d', 'bench_roles', *args]
    docker(*command)


def report(name, latencies, completed, elapsed, before, after):
    current, peak, cpu = after
    cpu_seconds = (cpu - before[2]) / 1e6
    result = {
        'role': name, 'completed': completed, 'seconds': round(elapsed, 3),
        'throughput_per_second': round(completed / elapsed, 2),
        'latency_ms': {'p50': round(percentile(latencies, .50), 2), 'p95': round(percentile(latencies, .95), 2), 'p99': round(percentile(latencies, .99), 2)},
        'memory_current_mib': round(current / 1048576, 1), 'memory_peak_mib': round(peak / 1048576, 1),
        'cpu_seconds': round(cpu_seconds, 3), 'operations_per_cpu_second': round(completed / cpu_seconds, 2) if cpu_seconds else None,
    }
    print(json.dumps(result, sort_keys=True))
    return result


def benchmark_http(image, network, cpus, memory, requests, concurrency):
    name = 'odoo-bench-http'
    start(name, image, network, cpus, memory, '--runtime-role=http', '--workers=1', '--max-cron-threads=0', '--session-store=redis', '--redis-url=redis://redis:6379/0', ports=('18069:8069',))
    wait_http('http://127.0.0.1:18069')
    cookie = login('http://127.0.0.1:18069')
    before = usage(name)
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda _: rpc('http://127.0.0.1:18069', cookie, 'res.partner', 'search_read', [[], ['name', 'email']], {'limit': 20}), range(requests)))
    elapsed = time.perf_counter() - started
    after = usage(name)
    ok = [latency for success, latency in results if success]
    result = report('http', ok, len(ok), elapsed, before, after)
    result['errors'] = requests - len(ok)
    result['error_pct'] = round(result['errors'] / requests * 100, 2)
    docker('rm', '-f', name)
    return result


def benchmark_cron(image, network, cpus, memory, jobs):
    setup = """action=env['ir.actions.server'].create({'name':'Runtime benchmark cron action','model_id':env.ref('base.model_res_partner').id,'state':'code','code':"env['ir.config_parameter'].sudo().set_param('runtime.benchmark.cron', str(int(env['ir.config_parameter'].sudo().get_param('runtime.benchmark.cron', '0')) + 1))"})
env['ir.config_parameter'].sudo().set_param('runtime.benchmark.cron','0')
cron=env['ir.cron'].create({'name':'Runtime benchmark cron','ir_actions_server_id':action.id,'interval_number':1,'interval_type':'days','numbercall':-1,'doall':False,'active':False})
env.cr.commit()
print(cron.id)"""
    cron_id = int(shell(image, network, setup).strip().splitlines()[-1])
    name = 'odoo-bench-cron'
    start(name, image, network, cpus, memory, '--runtime-role=cron', '--workers=1', '--max-cron-threads=1', '--no-http')
    # WorkerCron can still be in initial 60s poll sleep when container starts.
    time.sleep(70)
    before = usage(name); started = time.perf_counter(); latencies = []
    for expected in range(1, jobs + 1):
        triggered = time.perf_counter()
        docker('exec', 'odoo-full-db', 'psql', '-U', 'odoo', '-d', 'bench_roles', '-c',
            "update ir_cron set active=true,nextcall=now() at time zone 'UTC' where id=%d" % cron_id)
        docker('exec', 'odoo-full-db', 'psql', '-U', 'odoo', '-d', 'postgres', '-c',
            "notify cron_trigger, 'bench_roles'")
        deadline = time.time() + 30
        while time.time() < deadline:
            result = docker('exec', 'odoo-full-db', 'psql', '-U', 'odoo', '-d', 'bench_roles', '-Atc',
                "select value from ir_config_parameter where key='runtime.benchmark.cron'")
            if int(result.stdout.strip() or 0) >= expected:
                latencies.append((time.perf_counter() - triggered) * 1000)
                break
            time.sleep(.02)
        else:
            raise RuntimeError('cron trigger timeout at %d' % expected)
    elapsed = time.perf_counter() - started; after = usage(name)
    result = report('cron', latencies, jobs, elapsed, before, after)
    docker('rm', '-f', name)
    docker('exec', 'odoo-full-db', 'psql', '-U', 'odoo', '-d', 'bench_roles', '-c',
        "delete from ir_cron where id=%d; delete from ir_act_server where name->>'en_US'='Runtime benchmark cron action'" % cron_id)
    return result

def benchmark_broker(image, network, cpus, memory, messages):
    topic = 'runtime.benchmark.%x' % random.getrandbits(32)
    setup = """topic=env['broker.topic'].create({'name':'%s'})
for i in range(%d): env['broker.publisher'].publish(topic.name, {'sequence':i})
env.cr.commit()
print(topic.id)""" % (topic, messages)
    topic_id = int(shell(image, network, setup).strip().splitlines()[-1])
    name = 'odoo-bench-broker'
    start(name, image, network, cpus, memory, '--runtime-role=broker', '--workers=0', '--no-http', '--broker-provider=nsq', '--broker-database=bench_roles', '--nsq-discovery=lookupd', '--nsqd-tcp-addresses=nsqd:4150', '--nsqlookupd-http-addresses=http://nsqlookupd:4161', '--broker-poll-seconds=.05', '--broker-batch-size=100')
    before = usage(name); started = time.perf_counter(); deadline = time.time() + 180
    count = 0
    while time.time() < deadline:
        result = docker('exec', 'odoo-full-db', 'psql', '-U', 'odoo', '-d', 'bench_roles', '-Atc',
            "select count(*) from broker_outbox where topic_id=%d and state='published'" % topic_id)
        count = int(result.stdout.strip() or 0)
        if count >= messages:
            break
        time.sleep(.05)
    elapsed = time.perf_counter() - started; after = usage(name)
    assert count == messages, f'broker published {count}/{messages}'
    result = report('broker', [elapsed * 1000 / messages] * messages, messages, elapsed, before, after)
    docker('rm', '-f', name)
    docker('exec', 'odoo-full-db', 'psql', '-U', 'odoo', '-d', 'bench_roles', '-c',
        "delete from broker_outbox where topic_id=%d; delete from broker_topic where id=%d" % (topic_id, topic_id))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', default='odoo16-engine:full-feature')
    parser.add_argument('--network', default='odoo-full-test')
    parser.add_argument('--cpu', type=float, default=.15)
    parser.add_argument('--http-memory', default='288m')
    parser.add_argument('--cron-memory', default='128m')
    parser.add_argument('--broker-memory', default='128m')
    parser.add_argument('--http-requests', type=int, default=1000)
    parser.add_argument('--http-concurrency', type=int, default=5)
    parser.add_argument('--cron-jobs', type=int, default=20)
    parser.add_argument('--broker-messages', type=int, default=5000)
    options = parser.parse_args()
    results = [
        benchmark_http(options.image, options.network, options.cpu, options.http_memory, options.http_requests, options.http_concurrency),
        benchmark_cron(options.image, options.network, options.cpu, options.cron_memory, options.cron_jobs),
        benchmark_broker(options.image, options.network, options.cpu, options.broker_memory, options.broker_messages),
    ]
    print(json.dumps({
        'cpu': options.cpu,
        'memory': {'http': options.http_memory, 'cron': options.cron_memory, 'broker': options.broker_memory},
        'results': results,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
