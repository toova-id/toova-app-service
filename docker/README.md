# Odoo engine base image

Image is extensible runtime base for downstream client images. It bundles Odoo 16 Community, runtime dependencies, patched-Qt wkhtmltopdf, and `id` translations; `en_US` remains source language. It does not bundle deployment config or client addons.

Downstream image:

```dockerfile
FROM ghcr.io/alner-repository/alner-odoo-engine:<immutable-tag>
USER root
COPY --chown=odoo:odoo requirements.txt /tmp/client-requirements.txt
RUN pip install --no-cache-dir -r /tmp/client-requirements.txt \
    && rm /tmp/client-requirements.txt
COPY --chown=odoo:odoo addons/ /mnt/extra-addons/
USER odoo
```

Mount client config at `/etc/odoo/odoo.conf`; keep custom addons in `/mnt/extra-addons`. Pin digest or immutable version tag, never `latest`, so HTTP/realtime, cron, broker, and migration jobs use identical engine source.

Build uses Odoo-compatible patched-Qt wkhtmltopdf `0.12.6.1-3` from its official GitHub release. Dockerfile pins release version and separate SHA-256 checksums for amd64 and arm64; checksum mismatch stops build.

Build:

```bash
docker buildx build --platform linux/amd64 \
  --build-arg PYTHON_VERSION=3.12 \
  -f docker/Dockerfile \
  -t odoo16-engine .

# Locale catalog defaults to id,en_US; override only for a deliberate base release.
docker buildx build --platform linux/arm64 \
  --build-arg ODOO_LOCALES=id,en_US \
  -f docker/Dockerfile \
  -t odoo16-engine:id .
```

Network access to `github.com/wkhtmltopdf/packaging` is required during build. Base image intentionally keeps full Community runtime catalog and common Odoo dependencies; client repositories own private dependency installation. Test-only addons and test directories are excluded from release image.

Recommended common config:

```ini
list_db = False
db_maxconn = 4
registry_signaling = event
registry_signaling_reconcile_seconds = 60
limit_request = 4000
limit_request_jitter = 800
limit_time_worker = 3600
limit_time_worker_jitter = 600
preload_gc_freeze = True
log_performance_sample_rate = 0.01
log_performance_slow_ms = 1000
```

Do not use one worker config for every role. HTTP uses `workers=1,max_cron_threads=0`;
cron uses `workers=1,max_cron_threads=1`; realtime and broker use `workers=0`.

Stateless HTTP replicas:

```ini
runtime_role = http
attachment_store = s3
s3_bucket = private-odoo-attachments
s3_prefix = odoo
s3_region = ap-southeast-3
# Optional for MinIO, Cloudflare R2, or another S3-compatible provider:
# s3_endpoint_url = https://example.r2.cloudflarestorage.com
session_store = redis
redis_url = redis://redis:6379/0
redis_session_prefix = odoo:session:
```

S3 credentials use standard AWS SDK chain: workload identity/IAM role, environment, or shared AWS config. Keep access keys out of `odoo.conf`.

Dedicated realtime pod:

```bash
/opt/odoo/odoo-bin gevent --config=/etc/odoo/odoo.conf \
  --database=production --runtime-role=realtime \
  --workers=0 --max-cron-threads=0 \
  --session-store=redis --redis-url=redis://redis:6379/0
```

Route `/websocket*` to realtime port `8072`; route all other paths to HTTP `8069`.
See `k8s/odoo-routing-example.yaml`.

Dedicated cron pod:

```bash
/opt/odoo/odoo-bin --config=/etc/odoo/odoo.conf \
  --database=production --runtime-role=cron \
  --workers=1 --max-cron-threads=1 --no-http
```

Dedicated broker pod:

```ini
runtime_role = broker
broker_provider = nsq
broker_database = production
broker_topic_prefix = production.odoo
nsq_discovery = lookupd
nsqd_tcp_addresses = nsqd-0:4150,nsqd-1:4150
nsqlookupd_http_addresses = http://lookupd-0:4161,http://lookupd-1:4161
```

Local stack and checks:

```bash
docker compose -f docker/docker-compose.test.yml up -d
python3 scripts/test_multi_replica.py
python3 scripts/test_runtime_failures.py
curl --fail http://127.0.0.1:8072/websocket/health

python3 scripts/benchmark_runtime_roles.py \
  --cpu .15 --http-memory 288m --cron-memory 128m --broker-memory 128m \
  --http-requests 1000 --http-concurrency 5 \
  --cron-jobs 20 --broker-messages 5000
```

Read-only attachment audit:

```bash
docker compose -f docker/docker-compose.test.yml run --rm --no-deps \
  --entrypoint /opt/odoo/odoo-bin odoo-init \
  storage --config=/etc/odoo/odoo.conf -d test_ci \
  --no-http --log-level=error --include-orphans
```

Exit `0` means no referenced object missing/unavailable. Orphan output is report-only.
Never delete from orphan report automatically. Full operations guide:
[`../docs/runtime-roles-storage-operations.md`](../docs/runtime-roles-storage-operations.md).

Benchmark details and limits:
[`../docs/CHANGELOG-engine-optimization.md`](../docs/CHANGELOG-engine-optimization.md).

For PgBouncer transaction pooling, set direct PostgreSQL listener endpoint:

```ini
db_signaling_host = postgresql-primary.internal
db_signaling_port = 5432
```

Without direct endpoint, keep:

```ini
registry_signaling = poll
```

## Runtime import isolation

All roles load full installed model registry. HTTP controllers are loaded only by capable
roles for migrated core addons. Cron and broker avoid normal controllers; realtime loads bus
controllers only. `runtime_role=all` remains compatibility mode.

Optional PDF, OpenSSL/cryptography, docutils, ReportLab, and wkhtmltopdf initialization is
lazy. First related operation pays initialization cost. See measured footprint and custom
addon compatibility limit in
[`../docs/runtime-roles-storage-operations.md`](../docs/runtime-roles-storage-operations.md).
