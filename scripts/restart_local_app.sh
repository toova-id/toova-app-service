#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
IMAGE=${ODOO_IMAGE:-odoo16-engine:toova-demo}
NETWORK=${ODOO_NETWORK:-erp-local}
DB_HOST=${ODOO_DB_HOST:-erp-local-db}
DB_NAME=${ODOO_DB_NAME:-erp_local}
REDIS_CONTAINER=${ODOO_REDIS_CONTAINER:-erp-local-redis}
REALTIME_CONTAINER=${ODOO_REALTIME_CONTAINER:-erp-local-realtime}
APP_CONTAINER=${ODOO_APP_CONTAINER:-erp-local-app}
REDIS_URL=${ODOO_REDIS_URL:-redis://$REDIS_CONTAINER:6379/0}
REALTIME_URL=${ODOO_REALTIME_URL:-ws://127.0.0.1:8072/websocket}

if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
  docker network create "$NETWORK" >/dev/null
fi
if ! docker inspect "$REDIS_CONTAINER" >/dev/null 2>&1; then
  docker run -d --name "$REDIS_CONTAINER" --network "$NETWORK" --restart unless-stopped \
    redis:7-alpine redis-server --save '' --appendonly no >/dev/null
elif [ "$(docker inspect -f '{{.State.Running}}' "$REDIS_CONTAINER")" != true ]; then
  docker start "$REDIS_CONTAINER" >/dev/null
fi
for _ in $(seq 1 30); do
  docker exec "$REDIS_CONTAINER" redis-cli ping 2>/dev/null | grep -q PONG && break
  sleep 1
done

docker rm -f "$APP_CONTAINER" "$REALTIME_CONTAINER" erp-local-proxy >/dev/null 2>&1 || true

docker run -d --name "$APP_CONTAINER" --network "$NETWORK" --restart unless-stopped -p 8069:8069 \
  -v erp-local-odoo-data:/var/lib/odoo \
  "$IMAGE" \
  --db_host="$DB_HOST" --db_port=5432 --db_user=odoo --db_password=odoo \
  -d "$DB_NAME" --no-database-list --runtime-role=http --workers=1 --max-cron-threads=0 --registry-signaling=poll \
  --session-store=redis --redis-url="$REDIS_URL" --attachment-store=file --log-level=info >/dev/null

docker run -d --name "$REALTIME_CONTAINER" --network "$NETWORK" --restart unless-stopped -p 8072:8072 \
  -v erp-local-odoo-data:/var/lib/odoo \
  "$IMAGE" gevent \
  --db_host="$DB_HOST" --db_port=5432 --db_user=odoo --db_password=odoo \
  -d "$DB_NAME" --no-database-list --runtime-role=realtime --workers=0 --max-cron-threads=0 --registry-signaling=poll \
  --session-store=redis --redis-url="$REDIS_URL" --attachment-store=file --gevent-port=8072 --log-level=info >/dev/null

for _ in $(seq 1 60); do
  http_ok=0; realtime_ok=0
  curl --fail --silent http://127.0.0.1:8069/web/health >/dev/null && http_ok=1
  curl --fail --silent http://127.0.0.1:8072/websocket/health >/dev/null && realtime_ok=1
  if [ "$http_ok" = 1 ] && [ "$realtime_ok" = 1 ]; then
    docker exec -i "$APP_CONTAINER" python /opt/odoo/odoo-bin shell \
      --db_host="$DB_HOST" --db_port=5432 --db_user=odoo --db_password=odoo -d "$DB_NAME" --no-http \
      --registry-signaling=poll --session-store=redis --redis-url="$REDIS_URL" --attachment-store=file <<PY >/dev/null
param = env['ir.config_parameter'].sudo()
param.set_param('managed.realtime_url', '$REALTIME_URL')
env.cr.commit()
PY
    exit 0
  fi
  sleep 2
done
docker logs --tail 100 "$APP_CONTAINER" >&2
docker logs --tail 100 "$REALTIME_CONTAINER" >&2
exit 1
