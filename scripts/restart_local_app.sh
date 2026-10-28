#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=${ODOO_IMAGE:-odoo16-engine:settings-final}
docker rm -f erp-local-app >/dev/null 2>&1 || true
docker run -d --name erp-local-app --network erp-local --restart unless-stopped -p 8069:8069 \
  -v erp-local-odoo-data:/var/lib/odoo \
  -v "$ROOT/managed/core/static/app:/opt/odoo/managed/core/static/app:ro" \
  "$IMAGE" \
  --db_host=erp-local-db --db_port=5432 --db_user=odoo --db_password=odoo \
  -d erp_local --workers=0 --max-cron-threads=0 --registry-signaling=poll \
  --session-store=file --attachment-store=file --log-level=info >/dev/null
for _ in $(seq 1 60); do
  curl --fail --silent http://127.0.0.1:8069/web/health && exit 0
  sleep 2
done
docker logs --tail 100 erp-local-app >&2
exit 1
