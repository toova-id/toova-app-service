#!/usr/bin/env python3
"""Static contract check for downstream Odoo base-image consumers."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
dockerfile = (ROOT / 'docker/Dockerfile').read_text()
dockerignore = (ROOT / '.dockerignore').read_text().splitlines()
workflow = (ROOT / '.github/workflows/build-engine.yml').read_text()

assert 'ARG ODOO_LOCALES=id,en_US' in dockerfile
assert 'AS source-pruner' in dockerfile
assert 'AS frontend-builder' in dockerfile
assert 'RUN --mount=type=cache,target=/root/.npm npm ci' in dockerfile
assert 'COPY --from=source-pruner --chown=odoo:odoo /src /opt/odoo' in dockerfile
assert 'COPY --from=frontend-builder --chown=odoo:odoo /src/addons/web/static/app' in dockerfile
assert '/mnt/extra-addons' in dockerfile
assert 'USER odoo' in dockerfile
assert 'RUN if [ "${ODOO_STRIP_TESTS}" = "0" ]' not in dockerfile
assert 'PYTHONOPTIMIZE' not in dockerfile
assert 'addons' not in dockerignore
assert 'ODOO_LOCALES=id,en_US' in workflow
assert 'if [ "$SIZE" -gt 900 ]' in workflow
assert not (ROOT / 'Dockerfile').exists()

print('base image contract self-check passed')
