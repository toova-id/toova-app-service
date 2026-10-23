# Runtime Roles and Object Storage Operations

This document is production runbook for isolated Odoo runtime roles, Redis sessions,
S3-compatible attachment storage, health probes, and safe storage audits.

Current implementation commits:

```text
0f89bdbb  replace GCS attachment storage with S3
334dcfdc  defer optional runtime imports
bd049bca  minimize isolated runtime roles
4ec99cde  stream S3 attachments through signed URLs
62c8545e  keep generated CSS on Odoo origin
65eaf974  harden production runtime roles
b96b7756  isolate role-specific runtime imports
```

## 1. Production topology

Every role must run same immutable image digest and same addon revision.

```text
Ingress
  /websocket*  -> odoo-realtime:8072
  everything else -> odoo-http:8069

odoo-http       master + WorkerHTTP; normal HTTP/RPC only
odoo-realtime   one gevent process; websocket/bus routes only
odoo-cron       master + WorkerCron; scheduled actions only
odoo-broker     one process; outbox relay and optional consumer

Shared state
  PostgreSQL    business data, attachment metadata, registry generations, broker outbox/inbox
  Redis         HTTP/realtime sessions
  S3/R2         attachment binaries and generated assets
  NSQ           broker transport
```

Reference manifests:

```text
k8s/odoo-runtime-example.yaml
k8s/odoo-routing-example.yaml
```

No shared filestore PVC is required when `attachment_store=s3`. `/web/static` stays in
immutable image. Pod-local `/var/lib/odoo` and `/tmp` are ephemeral scratch space only.

## 2. Why every role loads registry

All roles use Odoo ORM and therefore need full model registry. Full registry preserves
model inheritance, fields, ACL, record rules, multi-company behavior, computed fields,
and addon hooks. This is different from loading every HTTP controller.

| Capability | HTTP | Realtime | Cron | Broker |
|---|---:|---:|---:|---:|
| Full installed model registry | yes | yes | yes | yes |
| Normal web controllers | yes | no | no | no |
| Bus/websocket controllers | yes | yes | no | no |
| Redis session access | yes | yes | no | no |
| HTTP worker | yes | no | no | no |
| Gevent websocket server | no | yes | no | no |
| Cron scheduler | no | no | yes | no |
| Broker relay/consumer | no | no | no | yes |

Role-aware server-wide preload:

```text
all       base, web, configured modules
http      base, web, configured modules
realtime  base, bus, configured modules except web preload
cron      base, configured modules except web preload
broker    base, configured modules except web preload
```

Core addon controller imports are role-gated for `base`, `web`, `bus`, `base_import`,
`auth_totp`, and `web_editor`. Model imports remain active on every role.

Compatibility ceiling: custom addons still execute their package `__init__.py`. A custom
addon that imports controllers unconditionally can still load them in cron/broker. Fix that
addon explicitly or introduce manifest-based runtime components after compatibility testing.
Do not create partial model registries.

## 3. Role commands

HTTP:

```bash
/opt/odoo/odoo-bin --config=/etc/odoo/odoo.conf \
  --database=production --runtime-role=http \
  --workers=1 --max-cron-threads=0 \
  --session-store=redis --redis-url=redis://redis:6379/0
```

Realtime:

```bash
/opt/odoo/odoo-bin gevent --config=/etc/odoo/odoo.conf \
  --database=production --runtime-role=realtime \
  --workers=0 --max-cron-threads=0 \
  --session-store=redis --redis-url=redis://redis:6379/0
```

Cron:

```bash
/opt/odoo/odoo-bin --config=/etc/odoo/odoo.conf \
  --database=production --runtime-role=cron \
  --workers=1 --max-cron-threads=1 --no-http
```

Broker:

```bash
/opt/odoo/odoo-bin --config=/etc/odoo/odoo.conf \
  --database=production --runtime-role=broker \
  --workers=0 --no-http \
  --broker-provider=nsq --broker-database=production
```

`runtime_role=all` remains compatibility mode. It keeps upstream-style combined services
and full controller imports; do not use it for new isolated production deployments.

## 4. Health contract

| Role | Probe | Meaning |
|---|---|---|
| HTTP liveness | `GET /web/health` | HTTP process responds |
| HTTP readiness | `GET /web/health?db_server_status=1` | HTTP plus database readiness |
| Realtime | `GET :8072/websocket/health` | gevent route responds |
| Cron | `/tmp/odoo-cron-health`, age `<15s` | WorkerCron heartbeat thread alive |
| Broker | `/tmp/odoo-broker-health`, age `<30s` | relay thread, relay heartbeat, and consumer thread healthy |

Cron heartbeat is independent from current job duration, so long jobs do not cause false
failures. Broker deletes health file and exits when relay or configured consumer dies.
Health files are process-local and must live on writable `/tmp`.

## 5. Registry signaling

Recommended when every role can reach direct PostgreSQL session endpoint:

```ini
registry_signaling = event
registry_signaling_reconcile_seconds = 60
```

`event` uses PostgreSQL `LISTEN/NOTIFY` plus periodic sequence reconciliation. Notifications
are fast path; database sequences remain source of truth after reconnect or missed events.

PgBouncer transaction pooling does not support durable `LISTEN`. Configure direct endpoint:

```ini
db_signaling_host = postgresql-primary.internal
db_signaling_port = 5432
```

If no direct/session-pooled endpoint exists, use:

```ini
registry_signaling = poll
```

Production gate: test disconnect, listener backend termination, reconnect, missed
notification reconciliation, database restore generation decrease, and rolling replicas.

## 6. S3/R2 attachment configuration

```ini
attachment_store = s3
s3_bucket = private-odoo-attachments
s3_prefix = odoo/production
s3_region = auto
s3_endpoint_url = https://ACCOUNT_ID.r2.cloudflarestorage.com
s3_download_url_seconds = 300
```

Credentials use standard boto3/AWS chain. Kubernetes injects them from Secret or workload
identity. Never store access key or secret in Git, config file, image, command history, or
support transcript.

Common environment variables for R2:

```text
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION=auto
AWS_EC2_METADATA_DISABLED=true   # useful only when no metadata service should be queried
```

Object layout:

```text
<s3_prefix>/<database>/<checksum-prefix>/<sha1>
```

Database stores pseudo-path such as:

```text
s3://ab/abcdef...
```

`s3_prefix` and database name determine physical object key. Treat prefix as immutable after
deployment. Changing it without copying objects makes every attachment appear missing.

## 7. Attachment delivery behavior

```text
normal attachment
  Odoo evaluates ACL/record rules
  Odoo returns temporary 302 signed URL
  Cache-Control: private, no-store
  R2 sends binary directly

generated CSS /web/assets/*.css
  stored in S3/R2
  proxied through Odoo
  Cache-Control: public, max-age=31536000, immutable
  root-relative /web/static URLs remain on Odoo origin

image resize/crop
  Odoo reads source object and performs requested transform

/web/static/*
  served from immutable image, never R2
```

Signed URL carries MIME type and `Content-Disposition`. Redirect is temporary (`302`), not
permanent (`301`). Generated CSS must not redirect to raw object-storage origin because its
root-relative font/static URLs would resolve against wrong host.

## 8. S3 failure semantics

| Storage result | Odoo result | Operator action |
|---|---|---|
| `404`, `NoSuchKey`, `NotFound` | `MissingError` | restore/copy missing object; investigate migration or deletion |
| `400/401/403`, invalid key/signature/token | `AccessError` | fix credentials, endpoint, clock, or bucket policy |
| missing credential chain | `AccessError` | restore Secret/workload identity |
| `429`, `5xx`, endpoint/network/BotoCore failure | `503 Service Unavailable` | retry with backoff; inspect provider health |
| concurrent conditional create `409/412` | success | existing content-addressed object won race |

Reads never convert S3 failure to empty bytes. This prevents silent data corruption.

S3 client is cached by PID, endpoint, and region. Forked workers create their own client and
connection pool; no boto3 client is shared across fork.

## 9. Write and delete safety

Writes use content-addressed SHA-1 key and conditional create:

```text
PutObject If-None-Match: *
```

Duplicate concurrent upload is safe.

Deletion runs only after attachment metadata transaction commits. Fresh transaction checks:

```sql
SELECT 1 FROM ir_attachment WHERE store_fname = %s LIMIT 1
```

Direct SQL is deliberate. ORM attachment search hides some binary-field (`res_field`)
attachments; ORM reference check could delete still-referenced object. Missing object during
delete is harmless. Other delete failures are logged and leave object intact.

Never bulk-delete object-storage keys based only on prefix listing.

## 10. Read-only storage audit

Command:

```bash
/opt/odoo/odoo-bin storage \
  --config=/etc/odoo/odoo.conf \
  --database=production \
  --no-http --log-level=error
```

Include orphan report:

```bash
/opt/odoo/odoo-bin storage \
  --config=/etc/odoo/odoo.conf \
  --database=production \
  --no-http --log-level=error \
  --include-orphans
```

Fast sample:

```bash
/opt/odoo/odoo-bin storage ... --storage-limit=100
```

JSON fields:

```text
database             audited database
attachment_rows      S3 metadata rows read, including res_field attachments
unique_objects       deduplicated referenced object keys checked
missing_objects      referenced keys returning missing
unavailable_objects  permission, credential, throttling, network, or provider failures
orphan_objects       prefix keys not referenced by audited metadata; only with --include-orphans
ok                    true only when missing and unavailable lists are empty
```

Exit code:

```text
0  audit completed, no referenced object missing/unavailable
1  at least one referenced object missing or unavailable
```

`orphan_objects` does not make `ok=false`; report is advisory and never deletes. Also note:
`--storage-limit` plus `--include-orphans` compares listed objects against limited metadata,
so it can report false orphans. Use unlimited audit before any orphan decision.

Safe workflow:

1. Run unlimited audit without orphan listing.
2. Resolve all `missing_objects` and `unavailable_objects` until `ok=true`.
3. Run unlimited audit with `--include-orphans`.
4. Export report and compare with retention/migration history.
5. Keep suspected orphan keys through soak/rollback window.
6. Delete only after explicit human approval and independently verified backup/rollback.

## 11. Prefix migration

To change bucket, prefix, or database name:

1. Freeze metadata writes or use controlled maintenance window.
2. Run source audit; require `ok=true`.
3. Copy objects non-destructively to exact target key layout.
4. Verify target object count, unique checksum count, size, and sampled hashes.
5. Start one canary role with target config against disposable or cloned database first.
6. Run target audit; require `missing_objects=[]`.
7. Roll all roles to same config/image.
8. Soak and repeat audit.
9. Keep old prefix as rollback copy.
10. Delete old prefix only after retention period and explicit approval.

Do not test alternate attachment backend against live database. `force_storage()` changes
metadata and can point live records at ephemeral local files.

## 12. Failure and replica tests

Multi-replica session/attachment test:

```bash
python3 scripts/test_multi_replica.py \
  --first=http://127.0.0.1:8069 \
  --second=http://127.0.0.1:8068 \
  --db=test_ci
```

Credential and endpoint failure test:

```bash
python3 scripts/test_runtime_failures.py \
  --image=odoo16-engine:test \
  --network=docker_default \
  --config=docker/odoo.conf \
  --env-file=docker/.env.r2
```

Role import footprint:

```bash
python /opt/odoo/scripts/benchmark_role_imports.py \
  --role=cron --database=benchmark \
  --config=/etc/odoo/odoo.conf \
  --attachment-store=file --registry-signaling=poll
```

Release image prunes `scripts/`; run benchmark from source/test image or mount script.

Minimum production failure matrix:

```text
R2 404                    explicit missing object
R2 403/bad credential     explicit access/config failure
R2 timeout/429/5xx        503 and recovery after provider returns
Redis unavailable         HTTP readiness failure; no split sessions
PostgreSQL unavailable    every DB-dependent readiness fails
NSQ unavailable           broker unhealthy; outbox intent remains recoverable
realtime unavailable      HTTP remains healthy
cron unavailable          HTTP, broker, realtime remain healthy
one HTTP replica exits    other replica preserves Redis session and R2 access
registry listener exits   reconnect plus authoritative reconciliation
```

## 13. Verified measurements

Registry benchmark used same Docker image base, disposable PostgreSQL database, and eight
installed addons: `base`, `web`, `bus`, `base_import`, `auth_totp`, `web_editor`,
`web_tour`, `web_kanban_gauge`.

```text
role       old RSS   new RSS   old modules  new modules  controllers after
HTTP       99.5MiB   87.9MiB   1066         951          29
cron       99.6MiB   86.4MiB   1066         913           0
broker    100.3MiB   86.3MiB   1066         913           0
realtime  100.5MiB   86.2MiB   1066         916           3
```

Cold `import odoo`:

```text
RSS       76.4MiB -> 72.5MiB
modules   796 -> 758
PyPDF2 modules 30 -> 0
```

Final disposable live runtime after health and functional operations:

```text
HTTP worker  about 78MiB RSS
cron worker  about 72MiB RSS
broker       about 66MiB container memory
realtime     about 71MiB container memory
```

These are engine footprint measurements, not production sizing promises. Installed client
addons and first-use PDF/mail/image code increase memory.

## 14. Lazy optional stacks

The following load on first use instead of every process bootstrap:

```text
PyPDF2 and compatibility decompression patch
OpenSSL/cryptography SMTP certificate path
docutils module-description rendering
ReportLab barcode runtime
wkhtmltopdf version probe
PIL report image conversion where possible
test loader/result
CLI and broker service packages
```

PyPDF2 patch, ReportLab warmup, and wkhtmltopdf probe use locks for concurrent first use.
First PDF, certificate SMTP, module-description, or barcode operation pays initialization
cost. Prewarm only when workload needs it; do not force these stacks into broker/realtime.

## 15. Security and rollback

```text
Secrets              Kubernetes Secret/workload identity only
Objects              private by default
Authorization        Odoo ACL/record rule before signed redirect
Signed URL lifetime  short; default 300 seconds
Audit command         read-only
Orphan deletion       never automatic
Image rollout         same immutable digest across all roles
Prefix rollback       retain previous prefix through soak window
runtime rollback      runtime_role=all preserves compatibility behavior
signaling rollback    registry_signaling=poll
```

R2 is primary binary storage, not automatically backup. Database backup and object-storage
backup/versioning/replication need separate RPO/RTO decision. Custom backup/restore tooling
is intentionally out of current scope.
