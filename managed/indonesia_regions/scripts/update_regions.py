#!/usr/bin/env python3
"""Regenerate regions.csv from sources documented by @emsifa/wilayah skill."""

import csv
import re
import urllib.request
from pathlib import Path

REGIONS = 'https://raw.githubusercontent.com/cahyadsn/wilayah/refs/heads/master/db/wilayah.sql'
POSTAL = 'https://raw.githubusercontent.com/cahyadsn/wilayah_kodepos/refs/heads/main/db/wilayah_kodepos.sql'
ROWS = re.compile(r"\('([^']+)'\s*,\s*'((?:[^']|'')*)'\)")
TARGET = Path(__file__).parents[1] / 'data' / 'regions.csv'


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read().decode('utf-8-sig')


def main():
    regions = [(code, name.replace("''", "'")) for code, name in ROWS.findall(fetch(REGIONS))]
    postal = dict(ROWS.findall(fetch(POSTAL)))
    if len(regions) < 90000 or len(postal) < 80000:
        raise RuntimeError('Incomplete Indonesian region source.')
    with TARGET.open('w', encoding='utf-8', newline='') as output:
        writer = csv.writer(output)
        writer.writerow(['code', 'name', 'parent_code', 'level', 'postal_code'])
        for code, name in regions:
            parts = code.split('.')
            writer.writerow([code, name, '.'.join(parts[:-1]), len(parts), postal.get(code, '')])
    print(f'wrote {len(regions)} regions to {TARGET}')


if __name__ == '__main__':
    main()
