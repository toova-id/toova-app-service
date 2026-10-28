#!/usr/bin/env python3
"""Static regression check for automatic telemetry removed by this fork."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

removed_paths = (
    'src/addons/mail/models/update.py',
    'src/addons/mail/tests/test_update_notification.py',
    'src/addons/website_mail/models/update.py',
)
for path in removed_paths:
    assert not (ROOT / path).exists(), path

checks = {
    'src/addons/mail/data/ir_cron_data.xml': ('ir_cron_module_update_notification', 'publisher_warranty'),
    'src/odoo/tools/config.py': ('publisher_warranty_url', 'services.openerp.com'),
}
for path, forbidden in checks.items():
    source = (ROOT / path).read_text()
    for value in forbidden:
        assert value not in source, f'{value} remains in {path}'

assert "'manual'" in (ROOT / 'src/addons/crm/models/res_config_settings.py').read_text(), \
    'manual opt-in missing from src/addons/crm/models/res_config_settings.py'

print('Odoo telemetry removal self-check passed')
