#!/usr/bin/env python3
"""Small stdlib-only Odoo HTTP benchmark runner."""
import argparse
import concurrent.futures
import json
import math
import statistics
import time
import urllib.error
import urllib.request


def percentile(values, percent):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * percent / 100
    low = math.floor(index)
    high = math.ceil(index)
    if low == high:
        return values[low]
    return values[low] * (high - index) + values[high] * (index - low)


def request(url, timeout):
    started = time.perf_counter()
    status = 0
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        error.read()
        status = error.code
    except (OSError, TimeoutError):
        status = 0
    return status, time.perf_counter() - started


def run(url, requests, concurrency, timeout):
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(lambda _index: request(url, timeout), range(requests)))
    wall = time.perf_counter() - started
    latencies = [duration * 1000 for _status, duration in results]
    status_counts = {}
    for status, _duration in results:
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
    return {
        'url': url,
        'requests': requests,
        'concurrency': concurrency,
        'wall_seconds': wall,
        'requests_per_second': requests / wall,
        'latency_ms': {
            'mean': statistics.fmean(latencies),
            'p50': percentile(latencies, 50),
            'p95': percentile(latencies, 95),
            'p99': percentile(latencies, 99),
            'max': max(latencies),
        },
        'status_counts': status_counts,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8069/web/health')
    parser.add_argument('--requests', type=int, default=1000)
    parser.add_argument('--concurrency', type=int, default=10)
    parser.add_argument('--timeout', type=float, default=30)
    args = parser.parse_args()
    if args.requests < 1 or args.concurrency < 1 or args.timeout <= 0:
        parser.error('requests/concurrency must be positive and timeout greater than zero')
    print(json.dumps(run(args.url, args.requests, args.concurrency, args.timeout), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
