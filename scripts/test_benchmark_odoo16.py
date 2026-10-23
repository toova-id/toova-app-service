#!/usr/bin/env python3
from benchmark_odoo16 import percentile

assert percentile([1, 2, 3, 4], 50) == 2.5
assert round(percentile([1, 2, 3, 4], 95), 2) == 3.85
assert percentile([], 95) is None
print('benchmark self-check passed')
