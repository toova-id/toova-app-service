# Odoo 16 Engine Implementation Log

**New agent session? Start at [CHANGELOG-engine-optimization.md](CHANGELOG-engine-optimization.md) instead.** This file is
the chronological batch-by-batch detail; the changelog is the current-state summary and
handover point.

## Batch 1 — Instrumentation Foundation

Status: source implemented, integration benchmark pending.

Changed:

```text
odoo/http.py
odoo/sql_db.py
odoo/api.py
odoo/modules/registry.py
odoo/service/server.py
odoo/tools/config.py
```

Metrics added:

```text
HTTP total duration
routing duration
authentication duration
registry signaling duration
cursor checkout duration
DB connection checkout count/duration
SQL count/duration
flush count/duration
recompute count/records/duration
JSON decode/encode duration
response Content-Length
process RSS/PSS/USS/VMS
cgroup memory current/max
cgroup CPU quota/period/throttled time
DB pool used/count/max
cache clear entry count/caller at DEBUG
```

Configuration defaults:

```ini
log_performance_sample_rate = 0.0
log_performance_slow_ms = 0
```

Recommended benchmark configuration:

```ini
log_performance_sample_rate = 0.01
log_performance_slow_ms = 1000
log_handler = :INFO,odoo.modules.registry.cache:DEBUG
```

Operational notes:

- Normal request logs sampled deterministically.
- Slow request logs always emitted.
- URL query string, request body, RPC parameters, credentials, SQL text, and response body are not logged.
- Resource log emits at most once per 60 seconds per process.
- PSS/USS collection uses `memory_full_info()` only when `odoo.service.server.resources` DEBUG logging is active; INFO keeps low-cost RSS/VMS.
- Existing VMS worker limit behavior remains unchanged in this batch.

Validation completed:

```text
Python compileall: passed
git diff --check: passed
assert-based cgroup v1/v2 tests added
assert-based request sampling/redaction tests added
```

Validation blocked locally:

```text
full Odoo test startup: PyPDF2 missing from local Python 3.9 environment
benchmark environment and production snapshot: unavailable
```

## Batch 2 — Opt-in Runtime Controls

Implemented behind compatibility-preserving defaults:

```text
registry_signaling = poll | event
registry_signaling_reconcile_seconds = 60
db_signaling_host/db_signaling_port direct listener endpoint
http_max_inflight = 0
runtime_role = all | http | realtime | cron | broker
limit_request_jitter = 0
preload_gc_freeze = False
limit_memory_metric = vms | rss | pss | uss
```

Changes:

- Event signaling uses PostgreSQL `LISTEN/NOTIFY` plus sequence reconciliation.
- Notification carries DB and committed generation; payload contains no secret.
- One listener per database, because PostgreSQL delivers `NOTIFY` only inside the originating database.
- Listener uses direct unpooled session and reconnect backoff, and drops payloads from other databases.
- Listener state resets after fork, so worker processes never inherit parent generations.
- Signaling reads end their transaction immediately, so no idle-in-transaction session remains.
- Default remains polling until integration tests and PgBouncer routing pass.
- Admission rejects excess requests with HTTP `503` and `Retry-After: 1` before request/session/DB setup.
- Runtime roles separate HTTP, cron, and realtime processes.
- Worker recycle jitter and pre-fork `gc.freeze()` remain opt-in.
- Soft memory recycling can use RSS/PSS/USS; default VMS behavior remains.
- JSON decoder now accepts request bytes directly, removing one text allocation.

## Batch 3 — Build and Benchmark Foundations

Added:

```text
Dockerfile
.dockerignore
docker/odoo.conf.example
docker/README.md
scripts/benchmark_odoo16.py
scripts/test_benchmark_odoo16.py
scripts/prune_translations.py
scripts/test_prune_translations.py
k8s/odoo-runtime-example.yaml
```

Docker build requires verified patched-Qt wkhtmltopdf packages supplied by release pipeline, and verifies each package against a committed SHA-256 checksum file. No mutable binary download embedded.

Build argument `ODOO_LOCALES` prunes translation catalogs; omitting it keeps every catalog.

Added observability without new dependency:

```text
ormcache hit/miss per request
transaction flush time per request
in-flight request count per request
registry model and field count at load
```

Next required environment work:

```text
install complete Odoo dependencies
run base and test_http suites against PostgreSQL
run Community/Enterprise/custom addon install-update tests
build amd64/arm64 images with verified wkhtmltopdf packages
capture baseline and candidate benchmark runs
keep opt-in features disabled until their gates pass
```

## Batch 4 — Engine Hot Path, Signaling, Worker Lifecycle

Scope: `odoo/*.py` and engine tests only. No Docker, config-file, or deployment change.

### Request instrumentation fast path

```text
odoo/http.py       _start_request_performance() decides sampling before any timer runs
odoo/http.py       unsampled requests never create request_metrics nor thread attributes
odoo/http.py       failed HTTPRequest construction clears instrumentation thread state
odoo/sql_db.py     cursor checkout timing only when the thread opted in
odoo/service/model.py signaling timing only when the thread opted in
```

### Registry signaling

```text
update_signaling_state()     monotonic max(), delayed notifications cannot move state back
reconcile_signaling_state()  authoritative replace, allows decrease after database restore
SignalingListener.consume()  returns whether a generation gap needs reconciliation
SignalingListener.reconcile() reuses the durable LISTEN connection, no second connection
start_signaling_listener()   lock-free fast path once the listener thread is alive
pg_notify                    emitted only when registry_signaling == 'event'
```

### Worker lifecycle

```text
limit_time_worker         HTTP worker maximum age, default 0 (off)
limit_time_worker_jitter  deterministic per-generation offset, prevents simultaneous recycle
limit_memory_pressure     cgroup ratio guard, default 0.0 (off)
worker.recycle_reason     timeout | hard-memory | parent-changed | request-limit | max-age
                          | soft-memory | memory-pressure
hard-memory watchdog      parent kills the worker when metric != vms exceeds limit_memory_hard
memory pressure           pause spawning, retire the largest HTTP worker, keep at least one
gc.freeze/unfreeze        heap unfrozen once before a runtime registry replacement
```

### Rejected

```text
targeted ormcache invalidation (clear_cache(model, method) + LRU.clear_prefix)
```

Full `base` regression exposed `TestHasGroup.test_has_group_cleared_cache_on_write` staleness. Reverted to global `_clear_cache()`; `odoo/tools/lru.py` and `test_ormcache.py` restored to upstream behaviour.

### Verification

```text
base       0 failed, 0 error of 913 tests
test_http  0 failed, 0 error of 105 tests
excluded   TestQWebBasic.test_render_barcode (missing rlPyCairo)
excluded   TestRunnerLogging.test_assertQueryCount (Python 3.12 message format)
integration two prefork workers, event signaling, cache invalidation reached both workers
integration listener reconnected after pg_terminate_backend, health stayed pass
integration worker max-age recycling under continuous load, 0 failed request
```

### Signaling measurement

Two prefork workers, 400 requests per run, `/web/login`, alternating modes:

```text
poll   xact/req 0.948   tuples/req 31.1
event  xact/req 0.512   tuples/req 20.2
poll   xact/req 0.757   tuples/req 20.6
event  xact/req 0.510   tuples/req 20.1
```

Event mode removes the per-request signaling transaction in steady state. Latency and throughput deltas are not claimed: the local host applies no CPU limit and the workload is a single light endpoint.

### Still open

```text
realistic session workload (login, menu, ORM read, write, sale, invoice, stock)
baseline unmodified image versus candidate on identical resources
PgBouncer routing validation for LISTEN/NOTIFY
Community/Enterprise/custom addon install-update gate on Python 3.12
ORM hot path work, only after profiling a realistic workload
```

## Batch 5 — GKE Parity Local Run

### Resource parity applied

Compose now mirrors the GKE container, verified from inside the container:

```text
cpu.max      94000 100000     -> 0.94 CPU, GKE limit 940m
memory.max   2306867200       -> 2200Mi, GKE limit
reservation  2000m            -> GKE request 2000Mi
```

Earlier local runs applied no CPU limit at all (`NanoCpus=0`), so their throughput numbers were not comparable to GKE.

### Memory budget corrected

The previous config overcommitted the pod:

```text
before  3 workers x limit_memory_hard 950MB = 2.85GB > 2200Mi cgroup limit
after   3 workers x 550MB hard, 450MB soft, plus master and cron headroom
```

### Timeout split

```text
before  limit_time_cpu 900, limit_time_real 900 for every role
after   HTTP  limit_time_cpu 120, limit_time_real 180
        cron  limit_time_real_cron 900
```

A stuck HTTP worker previously held a slot for 15 minutes.

### Worker recycling relaxed

```text
before  limit_request 1000, jitter 200
after   limit_request 4000, jitter 800, limit_time_worker 3600, jitter 600
```

### Stress harness rewritten

The old script measured the wrong things:

```text
read host cgroup files, not the container under test
counted only status 0, 500, 503 as errors
inspected .State.RestartCount, a key that does not exist
hit /web/webclient/version_info with GET, which answers 400
```

Every point is fixed. Errors now include any non-2xx/3xx plus JSON-RPC fault bodies, resources come from the container cgroup, and the session workload calls `res.partner.search_read`, `res.users.read`, `ir.model.search_count` through `/web/dataset/call_kw`.

### Result under GKE parity

3 HTTP workers, 1 cron worker, CPU 0.94, memory limit 2200Mi:

```text
anonymous  concurrency 1..300   0 errors up to 100, 2.7% client timeouts at 200-300
session    concurrency 5..100   0 errors, p50 11-16ms, p95 76-1058ms
endurance  50 concurrent        0 errors across every iteration
memory     peak 364MiB of 2200MiB (13.1%), no OOM, no restart
recycles   request-limit 15, memory 0, timeout 0
```

Headroom is large: memory never passed 17% of the pod limit, so CPU is the binding resource at 940m, not memory.

### Observed cost centre

```text
/web/database/selector   192ms idle, saturates all 3 workers under load
/web/login               2.5ms
/web/health              1.5ms
```

Production sets `list_db = False`, so the selector is not on the user path; it was removed from the workload mix.

## Batch 6 — S3/R2 Stateless Attachment Delivery

Implemented in commits `0f89bdbb`, `4ec99cde`, and `62c8545e`.

```text
GCS dependency              replaced by boto3 S3-compatible client
credentials                 standard AWS SDK chain; no secret in repository/config
client cache                PID + endpoint + region, safe after prefork
object writes               content-addressed PutObject with If-None-Match: *
normal downloads            Odoo ACL then short-lived signed 302 redirect
image transforms            read through Odoo when resize/crop requested
generated CSS               stored in R2, proxied through Odoo origin
/web/static                 immutable image source
object delete               post-commit and fresh direct-SQL reference check
```

Direct-SQL delete reference check fixed a critical bug: ORM attachment search hides some
`res_field` binary attachments and could classify a referenced content-addressed object as
orphan. Audit and migration code explicitly includes those rows.

Live R2 verification:

```text
HeadBucket, PutObject, GetObject, conditional create, DeleteObject pass
signed MIME and Content-Disposition pass
CSS, icon fonts, FontAwesome, favicon pass
metadata rows 198, present 198, missing 0
unique referenced objects 66, orphan report 0 at final audit
```

Old prefix stayed as rollback copy. No automatic object deletion was added.

## Batch 7 — Runtime Health, Multi-replica, and Storage Audit

Implemented in commit `65eaf974`.

```text
HTTP replicas             two Compose services, Redis sessions, shared R2 attachments
realtime                  dedicated gevent role and /websocket ingress routing
cron health               heartbeat thread writes /tmp/odoo-cron-health
broker health             checks relay thread, heartbeat age, and consumer thread
storage CLI               read-only metadata/object integrity JSON and optional orphan report
R2 errors                 missing, access/config, and retryable 503 classes
Kubernetes                four role deployments, Secret env injection, probes, Services/Ingress
registry signaling        event selected in local example; poll fallback remains
```

Live functional gates:

```text
shared_session=true, shared_attachment=true across HTTP replicas
realtime /websocket/health pass
actual cron server action executes
actual outbox message reaches NSQ and state=published
bad credential and dead endpoint classified; storage command exits 1
all roles healthy, restart=0, OOM=false, no runtime error logs
```

## Batch 8 — Role-aware Imports and Lazy Heavy Libraries

Implemented in commit `b96b7756`.

All roles keep full installed model registry. Core controller imports are gated by role for
`base`, `web`, `bus`, `base_import`, `auth_totp`, and `web_editor`.

```text
HTTP       base + web preload; normal controllers
realtime   base + bus preload; bus/websocket controllers only
cron       base preload; no measured controller modules
broker     base preload; no measured controller modules
all        compatibility behavior
```

Lazy first-use stacks:

```text
PyPDF2 patch, wkhtmltopdf probe, ReportLab warmup
OpenSSL/cryptography SMTP certificate path
docutils module description rendering
PIL report image conversion
```

PyPDF2, wkhtmltopdf, and ReportLab initialization is locked/idempotent.

Measured registry footprint:

```text
role       old RSS   new RSS   old modules  new modules  controllers after
HTTP       99.5MiB   87.9MiB   1066         951          29
cron       99.6MiB   86.4MiB   1066         913           0
broker    100.3MiB   86.3MiB   1066         913           0
realtime  100.5MiB   86.2MiB   1066         916           3
```

Cold `import odoo`: `76.4MiB -> 72.5MiB`, modules `796 -> 758`, PyPDF2 modules
`30 -> 0`.

Validation:

```text
34 focused tests, 0 failed, 0 errors
runtime_role=all compatibility passes
HTTP cross-replica login/session/RPC passes
cron action, broker publish, realtime health pass
PDF merge, SMTP lazy path, docutils rendering pass
```

Compatibility ceiling: custom addon `__init__.py` can still import controllers
unconditionally. Do not implement partial model registry; add explicit manifest runtime
components only after broad addon install/update testing.
