#!/usr/bin/env python3
"""Measure registry import footprint for one configured runtime role."""
import argparse
import json
import resource
import sys
import time

import odoo
from odoo.tools import config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', choices=('all', 'http', 'cron', 'broker', 'realtime'), required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--config')
    options, remaining = parser.parse_known_args()

    arguments = ['-d', options.database, '--runtime-role=' + options.role, '--no-http', *remaining]
    if options.config:
        arguments.insert(0, '--config=' + options.config)
    config.parse_config(arguments)

    from odoo.service import server

    started = time.perf_counter()
    server.load_server_wide_modules()
    registry = odoo.modules.registry.Registry.new(options.database)
    elapsed = time.perf_counter() - started
    modules = set(sys.modules)
    print(json.dumps({
        'role': options.role,
        'seconds': round(elapsed, 4),
        'rss_mib': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        'modules': len(modules),
        'controllers': sum('.controllers' in module for module in modules),
        'web_controllers': sum(module.startswith('odoo.addons.web.controllers') for module in modules),
        'bus_controllers': sum(module.startswith('odoo.addons.bus.controllers') for module in modules),
        'reportlab': sum(module.startswith('reportlab') for module in modules),
        'pil': sum(module.startswith('PIL') for module in modules),
        'pypdf2': sum(module.startswith('PyPDF2') for module in modules),
        'openssl': sum(module.startswith(('OpenSSL', 'cryptography')) for module in modules),
        'docutils': sum(module.startswith('docutils') for module in modules),
    }, sort_keys=True))
    registry.delete(options.database)


if __name__ == '__main__':
    main()
