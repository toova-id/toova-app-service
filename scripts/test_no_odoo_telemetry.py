#!/usr/bin/env python3
"""Static regression check for automatic telemetry removed by this fork."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

removed_paths = (
    'addons/mail/models/update.py',
    'addons/mail/tests/test_update_notification.py',
    'addons/website_mail/models/update.py',
)
for path in removed_paths:
    assert not (ROOT / path).exists(), path

checks = {
    'addons/mail/data/ir_cron_data.xml': ('ir_cron_module_update_notification', 'publisher_warranty'),
    'addons/l10n_fr/__init__.py': ('publisher_warranty', 'update_notification'),
    'addons/l10n_fr_pos_cert/__init__.py': ('publisher_warranty', 'update_notification'),
    'odoo/tools/config.py': ('publisher_warranty_url', 'services.openerp.com'),
}
for path, forbidden in checks.items():
    source = (ROOT / path).read_text()
    for value in forbidden:
        assert value not in source, f'{value} remains in {path}'

for path in (
    'addons/crm/models/res_config_settings.py',
    'addons/crm_iap_enrich/__init__.py',
    'addons/crm_iap_enrich/models/crm_lead.py',
):
    assert "'manual'" in (ROOT / path).read_text(), f'manual opt-in missing from {path}'

print('Odoo telemetry removal self-check passed')
