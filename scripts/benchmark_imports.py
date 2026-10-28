#!/usr/bin/env python3
"""Measure cold-process Odoo import and base-module load cost."""
import resource
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]
if not (project_root / 'src/odoo').is_dir() and Path('/opt/odoo/src/odoo').is_dir():
    project_root = Path('/opt/odoo')
sys.path.insert(0, str(project_root / 'src'))

started = time.perf_counter()
import odoo
odoo_imported = time.perf_counter()

if '--base' in sys.argv:
    odoo.modules.module.initialize_sys_path()
    odoo.modules.module.load_openerp_module('base')
base_loaded = time.perf_counter()

print(
    f'import_odoo_s={odoo_imported - started:.4f} '
    f'load_base_s={base_loaded - odoo_imported:.4f} '
    f'rss_kib={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss} '
    f'modules={len(sys.modules)} '
    f'tests={sum(name.startswith("odoo.tests") for name in sys.modules)} '
    f'cli={sum(name.startswith("odoo.cli") for name in sys.modules)} '
    f'broker={sum(name.startswith("odoo.broker") for name in sys.modules)} '
    f'reportlab={sum(name.startswith("reportlab") for name in sys.modules)}'
)
