#!/usr/bin/env python3
"""Verify retained managed ERP addons form a complete dependency closure."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_ROOTS = {
    'account', 'account_debit_note', 'account_edi', 'account_edi_ubl_cii',
    'account_lock', 'account_payment', 'analytic', 'base_automation', 'calendar',
    'contacts', 'crm', 'delivery', 'delivery_stock_picking_batch', 'hr',
    'hr_attendance', 'hr_contract', 'hr_expense', 'hr_holidays', 'hr_maintenance',
    'hr_presence', 'hr_recruitment', 'hr_recruitment_skills', 'hr_skills',
    'hr_timesheet', 'hr_work_entry', 'hr_work_entry_contract',
    'hr_work_entry_holidays', 'l10n_id', 'l10n_id_efaktur',
    'l10n_id_efaktur_coretax', 'maintenance', 'contact_persons', 'core', 'customers',
    'directory', 'discuss', 'indonesia_regions', 'people', 'products', 'sales', 'settings', 'vendors', 'mrp', 'mrp_account',
    'mrp_landed_costs', 'mrp_product_expiry', 'mrp_repair', 'mrp_subcontracting',
    'mrp_subcontracting_account', 'payment', 'payment_custom', 'product_expiry',
    'project', 'project_hr_expense', 'project_mrp', 'project_purchase', 'purchase_mrp',
    'purchase_requisition_stock', 'purchase_stock', 'repair', 'sale_management',
    'sale_margin', 'sale_mrp', 'sale_project', 'sale_stock', 'sale_timesheet',
    'stock_account', 'stock_dropshipping', 'stock_landed_costs',
    'stock_picking_batch', 'web',
}
EXCLUDED = {
    'event', 'hw_drivers', 'l10n_us', 'mass_mailing', 'payment_paypal',
    'point_of_sale', 'pos_sale', 'survey', 'test_sale_product_configurators', 'website',
}

modules = {}
for addon_root in (ROOT / 'src/odoo/addons', ROOT / 'src/addons', ROOT / 'managed'):
    for manifest_path in addon_root.glob('*/__manifest__.py'):
        modules[manifest_path.parent.name] = (
            ast.literal_eval(manifest_path.read_text()), manifest_path
        )

missing_roots = PRODUCT_ROOTS - modules.keys()
assert not missing_roots, f'missing product roots: {sorted(missing_roots)}'
assert not EXCLUDED & modules.keys(), f'excluded addons retained: {sorted(EXCLUDED & modules.keys())}'
assert not any('odoo.addons.website' in path.read_text(errors='ignore') for path in (ROOT / 'src/addons/web').rglob('*.py')), \
    'web addon must not retain website-only test imports'
brand_sources = [ROOT / 'frontend', ROOT / 'managed', ROOT / 'docs', ROOT / 'src/addons/web/views', ROOT / 'src/addons/web/static/src/scss']
legacy_brand = 'lu' + 'ma'
assert not any(
    __import__('re').search(rf'(?<![A-Za-z]){legacy_brand}(?![A-Za-z])', path.read_text(errors='ignore'), __import__('re').IGNORECASE)
    for source in brand_sources for path in source.rglob('*')
    if path.is_file() and 'node_modules' not in path.parts and 'core/static/app' not in path.as_posix()
), 'legacy brand must not remain'
database_controller = (ROOT / 'src/addons/web/controllers/database.py').read_text()
assert "if not odoo.tools.config['list_db']" in database_controller and 'request.not_found()' in database_controller, \
    'database manager routes must be blocked for single-tenant runtime'
assert 'Kelola database' not in (ROOT / 'src/addons/web/views/webclient_templates.xml').read_text(), \
    'login page must not expose database management'
restart_script = (ROOT / 'scripts/restart_local_app.sh').read_text()
assert '--runtime-role=http' in restart_script and '--runtime-role=realtime' in restart_script, \
    'local stack must run isolated HTTP and realtime roles'
assert '--session-store=redis' in restart_script and 'managed.realtime_url' in restart_script, \
    'local HTTP/realtime roles must share Redis sessions and publish direct websocket URL'
assert 'nginx' not in restart_script.lower(), 'local realtime stack must not require nginx'
for init_path in (ROOT / 'managed').glob('*/tests/__init__.py'):
    for line in init_path.read_text().splitlines():
        if line.startswith('from . import '):
            module = line.rsplit(' ', 1)[-1]
            assert (init_path.parent / f'{module}.py').exists(), f'missing managed test module: {module}'

missing_dependencies = {
    (name, dependency)
    for name, (manifest, _) in modules.items()
    for dependency in manifest.get('depends', ())
    if dependency not in modules
}
assert not missing_dependencies, f'missing dependencies: {sorted(missing_dependencies)}'

base_manifest = modules['base'][0]
assert 'data/ir_module_module.xml' not in base_manifest['data'], \
    'upstream Enterprise upsell catalog must not load in managed ERP'
payment_providers = (ROOT / 'src/addons/payment/data/payment_provider_data.xml').read_text()
assert 'base.module_payment_custom' in payment_providers
assert 'base.module_payment_paypal' not in payment_providers, \
    'removed foreign providers must not remain in payment seed data'

print(f'managed addon scope self-check passed: {len(modules)} modules')
