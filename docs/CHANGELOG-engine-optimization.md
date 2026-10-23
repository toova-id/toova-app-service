# Odoo 16 Engine Optimization — Changelog and Handover

Single entry point. A new agent session should read this file first, then open the
referenced documents only when it needs the deeper detail.

```text
upstream base   odoo/odoo branch 16.0, commit 480c5f49
working tree    see git status and latest commits
scope lock      engine, tests, production image, CI, and documented privacy changes
never touch     alner-odoo-service-odoo (a different production image)
```

## 1. Goal

Reduce memory and CPU of stock Odoo 16 Community, raise throughput, stay stable under
overload, and keep addon compatibility and business behaviour unchanged.

Non-negotiable: correctness and security outrank any performance number. ORM semantics,
transactions, ACL, record rules, computed fields, multi-company, and addon inheritance
must not change.

## 2. Runtime profiles

Historical GKE parity benchmark profile:

```text
cpu     request 400m    limit 940m
memory  request 2000Mi  limit 2200Mi
runtime combined 3 HTTP workers + 1 cron worker, db_maxconn 16
```

Current isolated-role local/reference profile:

```text
HTTP      1 worker, max_cron_threads=0, 192Mi local limit
realtime  1 gevent process, workers=0, 128Mi local limit
cron      1 WorkerCron, 128Mi local limit
broker    1 process, 96Mi local limit
DB pool   db_maxconn=4 per process in local profile
```

Do not compare absolute memory/latency across these profiles as if resource topology were
identical.

## 3. What was actually changed in the engine

Configuration features remain compatibility-preserving unless stated otherwise. Runtime import
isolation and lazy optional-library loading apply automatically according to `runtime_role`;
`runtime_role=all` preserves combined-service behavior.

### 3.0 Current release state (commits through `b96b7756`)

```text
HTTP       normal controllers, Redis sessions, one or more isolated WorkerHTTP processes
realtime   dedicated gevent process, bus/websocket controllers only
cron       isolated WorkerCron, no HTTP controllers
broker     isolated outbox relay/consumer, no HTTP controllers or cron
storage    private S3-compatible object store; no shared filestore PVC
static     /web/static from immutable image; generated CSS stored in S3 but proxied by Odoo
routing    /websocket* to realtime; every other route to HTTP
```

Every role still loads full installed **model registry**. This is required for model
inheritance, ACL, record rules, multi-company, fields, computed methods, cron actions, and
broker handlers. Only role-specific controllers and services are excluded.

Operational source of truth:
[Runtime Roles and Object Storage Operations](runtime-roles-storage-operations.md).

### 3.1 New configuration options

| Option | Default | File | Purpose |
|---|---|---|---|
| `registry_signaling` | `poll` | `tools/config.py` | `poll` = upstream per-request query, `event` = LISTEN/NOTIFY |
| `registry_signaling_reconcile_seconds` | `60` | `tools/config.py` | Periodic authoritative resync interval |
| `db_signaling_host` / `db_signaling_port` | off | `tools/config.py` | Direct PostgreSQL endpoint for LISTEN/NOTIFY, bypasses transaction-pooled PgBouncer |
| `http_max_inflight` | `0` (off) | `tools/config.py` | Per-process admission control; useful only for threaded/gevent |
| `runtime_role` | `all` | `tools/config.py` | `all`, `http`, `cron`, `realtime`, `broker` |
| `session_store` | `file` | `tools/config.py` | Shared HTTP session backend: `file` or `redis` |
| `redis_url` / `redis_session_prefix` | local Redis / `odoo:session:` | `tools/config.py` | Redis connection and namespaced session keys |
| `attachment_store` | `file` | `tools/config.py` | Attachment backend: `file`, `db`, or `s3` |
| `s3_bucket` / `s3_prefix` / `s3_region` / `s3_endpoint_url` | off / `odoo` / off / off | `tools/config.py` | Private content-addressed S3 storage; optional S3-compatible endpoint |
| `s3_download_url_seconds` | `300` | `tools/config.py` | Signed object download lifetime |
| `broker_provider` | `none` | `tools/config.py` | Native broker provider; first provider `nsq` |
| `broker_database` | `--database` | `tools/config.py` | Exactly one database for broker role |
| `broker_topic_prefix` | `odoo` | `tools/config.py` | Physical transport topic namespace |
| `broker_poll_seconds` / `broker_batch_size` | `1.0` / `100` | `tools/config.py` | Transactional outbox relay controls |
| `broker_max_in_flight` / `broker_max_retries` | `10` / `5` | `tools/config.py` | Broker flow and retry defaults |
| `nsq_discovery` | `direct` | `tools/config.py` | `direct` nsqd or `lookupd` discovery |
| `nsqd_tcp_addresses` | `localhost:4150` | `tools/config.py` | Comma-separated NSQ TCP endpoints |
| `nsqlookupd_http_addresses` | off | `tools/config.py` | Comma-separated lookup discovery endpoints |
| `limit_request_jitter` | `0` | `tools/config.py` | Random extra requests before recycle, desynchronizes restarts |
| `limit_time_worker` | `0` (off) | `tools/config.py` | HTTP worker maximum age in seconds |
| `limit_time_worker_jitter` | `0` | `tools/config.py` | Deterministic per-generation offset on the age limit |
| `limit_memory_metric` | `vms` | `tools/config.py` | `vms` keeps upstream `RLIMIT_AS`, `rss` uses the parent watchdog |
| `limit_memory_pressure` | `0.0` (off) | `tools/config.py` | cgroup ratio that pauses worker spawning |
| `preload_gc_freeze` | `False` | `tools/config.py` | `gc.freeze()` before fork for copy-on-write sharing |
| `log_performance_sample_rate` | `0.0` | `tools/config.py` | Fraction of requests that collect metrics |
| `log_performance_slow_ms` | `0` | `tools/config.py` | Always log a request slower than this |

### 3.2 Registry signaling (`odoo/modules/registry.py`)

Upstream runs one signaling `SELECT` per request. Event mode replaces it with a
per-database `LISTEN` thread plus periodic reconciliation.

```text
_SIGNALING_CHANNEL          'odoo_registry_signaling'
SignalingListener           one thread per database, PostgreSQL NOTIFY is not cross-database
  .consume(payload)         returns True when a generation gap needs reconciliation
  .reconcile(connection)    reuses the durable LISTEN connection, opens no second connection
update_signaling_state()    monotonic max(); a delayed notification cannot move state back
reconcile_signaling_state() authoritative replace; allows a decrease after a database restore
start_signaling_listener()  lock-free fast path once the listener thread is alive
reset_signaling_after_fork()clears inherited listener state in a child process
mark_preload_heap_frozen()  records that the preload heap was frozen
unfreeze_preload_heap()     releases the permanent generation before a runtime registry reload
```

PostgreSQL sequences stay the source of truth. `pg_notify` is emitted only in `event`
mode. On reconnect or sequence gap, full reconciliation runs before trusting notifications.

### 3.3 Request instrumentation (`odoo/http.py`, `sql_db.py`, `api.py`, `tools/cache.py`, `service/model.py`)

Sampling is decided before any timer starts, so an unsampled request pays nothing.

```text
_start_request_performance()  returns (sampled, metrics, started); unsampled returns metrics None
                              unsampled requests never create request_metrics nor thread attributes
_log_request_performance()    emits one structured line
failed HTTPRequest build      clears request_metrics, db_checkout_count, db_checkout_time
sql_db.py                     cursor checkout timing only when the thread opted in
service/model.py              signaling timing only when the thread opted in
api.py                        flush and recompute timing only when the thread opted in
tools/cache.py                ormcache hit/miss counters only when the thread opted in
```

Metrics collected: json decode/encode, routing, authentication, registry signaling,
cursor checkout count and time, ormcache hit/miss, flush time, in-flight count.
No payload, credential, query string, SQL text, RPC parameter, or response body is logged.

### 3.4 Odoo-host telemetry removal

Removed automatic outbound reporting while retaining user-triggered Odoo-host services
such as payment, SMS, EDI, OAuth, geolocation, and manual IAP actions.

```text
mail publisher warranty       model, weekly cron, endpoint config, ACL, and tests removed
existing databases            mail 1.11 migration deletes the old cron and server action
French localization hooks     installation-time publisher pings removed
website_mail                  publisher payload extension removed
CRM lead enrichment           automatic Odoo IAP calls default off; explicit opt-in still works
```

The removed publisher payload contained database UUID/name/create date, Odoo version,
instance URL, installed apps, user counts/activity, enterprise code, and company contact data.

### 3.5 Worker lifecycle (`odoo/service/server.py`)

```text
worker.recycle_reason        timeout | hard-memory | parent-changed | request-limit
                             | max-age | soft-memory | memory-pressure
hard-memory watchdog         parent kills a worker when metric != vms exceeds limit_memory_hard
                             (upstream only enforced RLIMIT_AS, which needs metric vms)
max-age recycling            WorkerHTTP only, offset by generation so workers do not recycle together
cgroup_memory_pressure_reached()  reads cgroup v1 and v2 files directly
process_spawn                under pressure: pause spawning, keep at least one worker
retire_worker_under_memory_pressure()  graceful SIGINT to the largest HTTP worker
gc.freeze / gc.unfreeze      heap unfrozen once before a runtime registry replacement
resource logging             rss, pss, uss, vms, cgroup current/max, cpu quota/period, throttled usec
```

`pss`/`uss` come from `memory_full_info()` and are DEBUG only because they are expensive.

### 3.6 Stateless storage, runtime isolation, and broker foundation

```text
attachment_store=s3         private S3/R2 backend using AWS credential chain or workload identity
session_store=redis         shared HTTP/realtime sessions with TTL
runtime_role=http           HTTP workers only; no cron or gevent child
runtime_role=realtime       dedicated gevent bus/websocket runtime on port 8072
runtime_role=cron           WorkerCron only; no HTTP listener or controllers
runtime_role=broker         isolated registry/ORM broker process; no HTTP or cron service
broker.publisher            transactional ORM publish API
broker topic UI             topics, channels, handler binding, retry and DLQ policy
broker outbox/inbox         reliable publish intent and at-least-once idempotency
NSQ provider                native TCP publish/consume; direct or nsqlookupd discovery
S3 writes                   conditional create; concurrent duplicate upload is safe
S3 deletes                  post-commit plus direct-SQL reference check in fresh transaction
S3 reads                    404=MissingError, auth=AccessError, retryable/network=503
S3 HTTP delivery            ACL check then signed 302; transformed images stay through Odoo
generated CSS               S3-backed but Odoo-proxied to preserve root-relative static URLs
storage audit               read-only JSON CLI; missing/unavailable exit 1; optional orphan report
broker health               relay thread + heartbeat + configured consumer thread
cron health                 process-local heartbeat independent from long-running job
```

Defaults remain `file` attachments, filesystem sessions, and broker disabled, preserving
existing deployments. Broker handlers are trusted Python registrations, never arbitrary
model/method or UI-entered Python execution. Broker payloads require JSON objects; binary
content stays in S3 and messages carry IDs/references only. Orphan reporting never deletes
objects. Prefix changes require verified non-destructive copy and rollback retention.

### 3.7 Role-aware imports and lazy optional runtimes

Role-aware bootstrap removes web/controller code from processes that cannot serve it:

```text
HTTP       base + web preload; normal controllers
realtime   base + bus preload; 3 bus controller modules in measured addon set
cron       base preload; 0 controller modules in measured addon set
broker     base preload; 0 controller modules in measured addon set
all        compatibility mode; full controller behavior
```

Core controller gates cover `base`, `web`, `bus`, `base_import`, `auth_totp`, and
`web_editor`. Full model registry remains loaded on every role. Custom addons which import
controllers unconditionally can still load them; generic partial registries were rejected.

Optional stacks now initialize on first use:

```text
PyPDF2 compatibility patch      locked and idempotent
wkhtmltopdf version probe       locked and idempotent
ReportLab barcode warmup        locked and idempotent
OpenSSL/cryptography            SMTP certificate path only
docutils                        module-description rendering only
PIL report conversion           report image path only
CLI, broker service, tests      lazy package imports
```

Measured with same disposable database and eight installed core/web addons:

```text
role       old RSS   new RSS   old modules  new modules  controllers after
HTTP       99.5MiB   87.9MiB   1066         951          29
cron       99.6MiB   86.4MiB   1066         913           0
broker    100.3MiB   86.3MiB   1066         913           0
realtime  100.5MiB   86.2MiB   1066         916           3

cold import odoo: RSS 76.4MiB -> 72.5MiB; modules 796 -> 758; PyPDF2 30 -> 0
```

### 3.8 Production image and regression gate corrections

```text
Community addons             included in image; no runtime source bind mount required
base-image contract          clients inherit immutable digest and add code under /mnt/extra-addons
locale catalog               Indonesian plus source English only by default
source-prune stage           removed files never remain in lower runtime layers
Python assertions            enabled; PYTHONOPTIMIZE removed from production image
Dockerfile                   docker/Dockerfile is the single build definition
pull requests                build a test image and run regression suites
regression modules           base, test_http, web, mail, sale, account, stock
image smoke                  verifies key addon manifests, assertions, health, and wkhtmltopdf
```

Speculative targeted cache, flush, and recompute patches without dedicated tests or
benchmark proof were restored to the imported Odoo baseline. Event signaling, runtime
controls, and sampled instrumentation remain.

Measured arm64 base-image correction:

```text
before     1,567,276,290 bytes unpacked; 498,807,296 bytes gzip docker-save
candidate    773,199,866 bytes unpacked; 304,125,884 bytes gzip docker-save
change                 -50.7% unpacked;                 -39.0% compressed
```

Candidate retained 473 non-test Community addon manifests, patched wkhtmltopdf, runtime
assertions, Indonesian translation, and downstream `/mnt/extra-addons` extension path.

## 4. What was rejected, and why

**Targeted ormcache invalidation.** An attempt replaced the global `_clear_cache()`
with `clear_cache(model_name, method)` plus an `LRU.clear_prefix()` helper.
The full `base` regression failed `TestHasGroup.test_has_group_cleared_cache_on_write`:
targeted invalidation left `user.has_group` stale, which is an ACL correctness bug.
Everything was reverted; `odoo/tools/lru.py` and `test_ormcache.py` are back to upstream.

Roughly 108 call sites still invoke `clear_caches()` / `_clear_cache()`. Narrowing them
stays the largest remaining engine opportunity and the most dangerous one. Any retry must
first record the caller namespace map, then gate on ACL, record rules, multi-company,
language, view, and QWeb asset regressions.

**`http_max_inflight` as prefork admission control.** A prefork `WorkerHTTP` serves one
request at a time, so the process-local counter is almost always 0 or 1 and the overload
already queued in the socket backlog. The option is kept for threaded and gevent modes
only, and must not be presented as prefork protection.

## 5. Configuration bugs found and fixed

These were real defects in the tuned config, not preferences.

| Item | Before | After | Why |
|---|---|---|---|
| Memory budget | `limit_memory_hard 950MB` x 3 workers = 2.85GB | 550MB hard, 450MB soft | 2.85GB exceeds the 2200Mi cgroup limit; the pod would be OOM-killed before the soft limit fired |
| Hard limit enforcement | `limit_memory_hard` silently inert with `limit_memory_metric = rss` | parent watchdog kills the worker | upstream `set_limit_memory_hard()` only runs when the metric is `vms` |
| HTTP timeout | `limit_time_cpu 900`, `limit_time_real 900` | cpu 120, real 180 | a stuck HTTP worker held its slot for 15 minutes |
| Cron timeout | shared with HTTP | `limit_time_real_cron 900` | long jobs belong to the cron role |
| Recycling | `limit_request 1000`, jitter 200 | 4000, jitter 800, plus `limit_time_worker 3600` jitter 600 | recycling every 1000 requests churns PIDs and discards warm caches |
| Local CPU limit | none (`NanoCpus=0`) | `cpus: 0.94` | earlier local throughput numbers were meaningless against a 940m GKE limit |
| Worker age jitter | `random.SystemRandom()` per worker | deterministic `generation % (jitter + 1)` | random draws collided and recycled two workers at once, observed in an integration run |

## 6. Measurements

### 6.1 Signaling, poll versus event

Two prefork workers, 400 requests per run, `/web/login`, alternating modes:

```text
poll   xact/req 0.948   tuples/req 31.1
event  xact/req 0.512   tuples/req 20.2
poll   xact/req 0.757   tuples/req 20.6
event  xact/req 0.510   tuples/req 20.1
```

Event mode removes the per-request signaling transaction in steady state. Latency and
throughput deltas are deliberately not claimed from this run.

### 6.2 Load under GKE parity

Verified from inside the container: `cpu.max 94000 100000`, `memory.max 2306867200`.

```text
session workload   concurrency 5..100    0 errors, p50 11-16ms, p95 76-1058ms
anonymous ramp     concurrency 1..300    0 errors to 100, 2.7% client timeouts at 200-300
endurance          50 concurrent         0 errors on every iteration
memory             peak 364MiB of 2200MiB (13.1%), no OOM, no restart
recycles           request-limit 15, memory 0, timeout 0
```

Memory never passed 17% of the pod limit, so **CPU at 940m is the binding resource**,
not memory. Raising worker count without raising CPU will not help.

Endpoint cost measured at idle:

```text
/web/database/selector   192ms, saturates all 3 workers under load
/web/login                2.5ms
/web/health               1.5ms
```

Production sets `list_db = False`, so the selector is off the user path and was removed
from the workload mix.

### 6.3 Isolated minimum-resource roles

Measured locally on Linux/arm64 Docker with real PostgreSQL 15, Redis 7, nsqd, and
nsqlookupd. Candidate source preceded final `rl-renderPM` dependency correction, which
does not affect measured role paths. Every Odoo role had `150m` CPU. Workloads are
engine smoke benchmarks, not client-SLA claims.

```text
HTTP   288Mi  1 worker + realtime  1000 authenticated search_read, concurrency 5
       16.13 req/s; p50 200.79ms; p95 594.59ms; p99 699.05ms
       peak 268.5MiB; 0 errors; 107.54 operations/CPU-second

cron   128Mi  singleton             20 real NOTIFY-triggered ir.cron executions
       6.62 jobs/s; p50 134.74ms; p95 182.79ms; p99 316.93ms
       peak 98.0MiB; 0 errors; 299.82 operations/CPU-second

broker 128Mi  NSQ lookupd mode      5000 committed transactional-outbox messages
       129.32 msg/s; relay batch average 7.73ms/message
       peak 86.8MiB; 0 errors; 869.99 operations/CPU-second
```

HTTP overload at concurrency 25 produced `13.44 req/s`, p95 `2793.35ms`, and `2.8%`
timeouts. Therefore `150m` HTTP is a minimum request for light traffic, not a safe burst
limit. Use at least `384Mi` memory limit and scale before sustained CPU saturation.

Recommended starting resources from this run and latest role footprint:

```text
HTTP      request 150m/288Mi   limit 500m/384Mi   one worker; HPA CPU 65-70%
realtime  request  25m/64Mi    limit 150m/128Mi   dedicated gevent role
cron      request  50m/96Mi    limit 150m/128Mi   singleton initially
broker    request  50m/64Mi    limit 150m/96Mi    start singleton; queue-depth scaling later
```

These are engine starting points. PDF/mail/client addons need separate memory headroom and
representative workload measurement.

## 7. Test status

All test runs happen inside Docker; host Odoo dependencies are not required.

Focused stateless/broker suites:

```text
/base:TestBroker                    3 tests, 0 failed, 0 errors
/base:TestGCSAttachment            historical only; GCS backend has been replaced
/base:TestS3Attachment              8 tests, 0 failed, 0 errors
/base:TestServerResources          role preload, topology, cgroup, heartbeat checks pass
/base:TestRegistrySignaling        event signaling checks pass
/base:TestPyPdf2Runtime            concurrent lazy initialization passes
/base:TestWkhtmltopdfRuntime       concurrent lazy probe passes
/test_http:TestRedisSessionStore   1 test, 0 failed, 0 errors
```

Integration checks, all passing:

```text
two HTTP replicas share Redis session and S3 attachment access
realtime /websocket/health responds on dedicated gevent role
actual cron server action executes through dedicated WorkerCron
actual committed broker outbox message reaches NSQ and state=published
R2 Head/Put/Get/conditional-create/Delete and post-commit deletion
R2 404, bad credential, dead endpoint and retryable error classification
read-only storage audit: 198 metadata rows, 66 unique objects, missing=0, orphan=0
two prefork workers with registry_signaling=event; invalidation reached both workers
pg_terminate_backend on listener; automatic reconnect, health stayed pass
max-age recycling under continuous load; 0 failed requests, staggered restarts
broker SIGTERM graceful shutdown exits 0
role import regression: 34 tests, 0 failed, 0 errors
base image contract, translation prune, compileall, Compose config, YAML parse, diff whitespace
```

Focused additions pass. Full `/base` diagnostic run on current pruned-local environment
executed 920 tests. Four failures were unrelated to new stateless/broker paths:

```text
French translation assertion       locale deliberately pruned to id,en_US
.torrent MIME assertion             slim OS MIME database lacks mapping
barcode render backend              rl-renderPM was missing; dependency added, focused rerun passes
query-count traceback assertion     Python 3.12 formatting mismatch
```

New engine test files:

```text
odoo/addons/base/tests/test_registry_signaling.py
odoo/addons/base/tests/test_server_resources.py
odoo/addons/base/tests/test_s3_attachment.py
odoo/addons/base/tests/test_pypdf2_runtime.py
odoo/addons/test_http/tests/test_performance.py
```

Standalone and integration checks:

```text
python3 scripts/test_base_image_contract.py
python3 scripts/test_benchmark_odoo16.py
python3 scripts/test_prune_translations.py
python3 scripts/test_no_odoo_telemetry.py
python3 scripts/stress_test_odoo.py --self-check
python3 scripts/test_multi_replica.py
python3 scripts/test_runtime_failures.py
python3 -m py_compile scripts/benchmark_runtime_roles.py scripts/benchmark_role_imports.py
```

Storage audit:

```bash
odoo-bin storage --config=/etc/odoo/odoo.conf -d production --no-http --log-level=error
odoo-bin storage --config=/etc/odoo/odoo.conf -d production --no-http --log-level=error --include-orphans
```

Full command semantics and safe orphan workflow:
[runtime-roles-storage-operations.md](runtime-roles-storage-operations.md).

## 7.1 External-first broker management (working tree)

```text
topics       logical/physical names, exact external names, direction, ownership, JSON/raw/Odoo formats
channels     standalone form/list/search, registered handler or admin Python code, execution identity
inbound      native external JSON/raw normalization, dot-path ID/type/payload extraction, size limit
outbound     Odoo envelope, JSON payload-only, or raw UTF-8 serialization through transactional outbox
deliveries   per-channel inbox detail, duration, payload size, raw body, errors, dead letter, requeue
operations   topic/channel smart buttons, outbox/inbox search filters, execution logs
security     Python editable only by system administrators; external payload cannot choose user/company/model/method
```

Invalid external input is recorded as dead and ACKed to stop poison-message loops. Stable
external IDs provide idempotency; NSQ transport ID then body SHA-256 are fallbacks. Requeue
uses retained exact transport body through outbox. Payload retention can be disabled per topic.

Focused `/base:TestBroker`: 6 tests, 0 failed, 0 errors.

## 8. Working tree state

Use `git status --short --branch`; this document no longer snapshots mutable working-tree state.

## 9. How to reproduce the local run

```bash
docker compose -f docker/docker-compose.test.yml up -d db redis nsqlookupd nsqd
docker compose -f docker/docker-compose.test.yml run --rm odoo-init
docker compose -f docker/docker-compose.test.yml up -d odoo-test
docker inspect docker-odoo-test-1 --format 'NanoCpus={{.HostConfig.NanoCpus}} Memory={{.HostConfig.Memory}}'
python3 -u scripts/stress_test_odoo.py --container docker-odoo-test-1 --endurance-seconds 30 --timeout 15
docker compose -f docker/docker-compose.test.yml down -v

# Isolated 150m runtime benchmark. Creates disposable bench_roles database data.
python3 scripts/benchmark_runtime_roles.py \
  --cpu .15 --http-memory 288m --cron-memory 128m --broker-memory 128m \
  --http-requests 1000 --http-concurrency 5 \
  --cron-jobs 20 --broker-messages 5000
```

Run the engine suites against the same PostgreSQL container:

```bash
docker run --rm --network docker_default -v "$PWD:/src" -w /src \
  --entrypoint /src/odoo-bin odoo16-engine:test \
  --db_host=db --db_port=5432 --db_user=odoo --db_password=odoo \
  -d suite_base --init=base --without-demo=all --stop-after-init \
  --workers=0 --max-cron-threads=0 \
  --test-tags '/base,-/base:TestQWebBasic.test_render_barcode,-/base:TestRunnerLogging.test_assertQueryCount' \
  --log-level=test
```

Local facts that matter:

```text
container name        docker-odoo-test-1, not odoo-test-1
PostgreSQL data       tmpfs; every restart loses the schema, re-run odoo-init
credentials           PostgreSQL odoo/odoo, Odoo admin/admin, database test_ci
ports                 8069 HTTP, 8068 second HTTP replica, 8072 dedicated realtime
```

## 10. Environment traps already hit

Do not repeat these.

```text
docker exec ... ps aux         image has no ps; use docker stats or read /sys/fs/cgroup/*
timeout 180 ...                not present on macOS; use perl -e 'alarm N; exec @ARGV'
sed -i 's/x/y/' file           macOS sed differs; use a small Python script instead
python3 nested f-string quote  Python 3.9 on the host rejects it
nohup python3 script > log     stdout stays buffered; add -u
host disk exhaustion           OrbStack froze at 1.1GiB free; orbctl stop/start then prune
docker system prune -af        removed the local alner-odoo-service-odoo tag once; harmless but avoid
```

## 11. Open work, in priority order

1. **Realistic client workload.** Runtime-role benchmark now covers authenticated reads,
   cron execution, and outbox transport. Add partner writes, sale confirm, invoice post,
   stock validation, PDF, and client addons on a representative database.
2. **Baseline versus candidate.** Build an unmodified Odoo 16 image and compare on
   identical database snapshot, addons, resources, and workload. No performance claim is
   valid until this exists.
3. **Instrumentation overhead.** Measure sampling on versus off on the same workload.
4. **PgBouncer.** Validate `registry_signaling=event` through selected production routing;
   transaction pooling breaks `LISTEN`, so listener must use `db_signaling_host` /
   `db_signaling_port` direct PostgreSQL or session-pooled endpoint. Direct PostgreSQL
   reconnect and reconciliation pass locally; production PgBouncer topology remains open.
5. **Python 3.12 addon gate.** Install-update run across Community, Enterprise, and
   custom addons: `sale`, `account`, `stock`, `mail`, `bus`, `web`.
6. **Image size.** Current arm64 base candidate is about 773MB unpacked with Community
   runtime addons, Indonesian translation, reports, and common dependencies retained.
7. **Cache invalidation, retry.** Only after a caller namespace map exists and the ACL
   and multi-company regressions gate it. See section 4.
8. **ORM hot path.** Deferred on purpose. Touch only after a profiler on a realistic
   workload shows N+1 queries, redundant flushes, a recompute storm, prefetch misses, or a
   cache-clear storm.

## 12. Before production

```text
rotate admin_passwd            a production value was exposed earlier in this work
full regression                base, web, sale, account, stock, mail, bus
baseline comparison            with correct CPU and memory parity
event mode gate                keep registry_signaling=poll until PgBouncer routing passes
realtime deployment            manifest and routing exist; verify chosen ingress websocket behavior
db_maxconn accounting          value is per process; calculate across every replica and role
R2 durability                  primary object storage is not backup; define RPO/RTO and retention
prefix cleanup                 retain rollback prefix until soak and repeated missing=0 audit
```

## 13. Related documents

```text
docs/runtime-roles-storage-operations.md        production role/storage runbook and failure semantics
docs/odoo16-base-runtime-goal.md                base image, stateless Kubernetes, S3/Redis, broker goal
docs/odoo16-engine-optimization-plan.md         architecture analysis and bottleneck list
docs/odoo16-engine-benchmark-targets.md         numeric targets and measurement method
docs/odoo16-runtime-image-optimization-plan.md  image size and startup work
docs/odoo16-engine-implementation-log.md        chronological batch-by-batch log
```

Minimum-role absolute measurements are recorded, but optimization deltas still need an
unmodified baseline. Engine targets remain: memory down 20%, common p95 down 20%, write
p95 down 15%, throughput up 20%, CPU per request down 15%, PostgreSQL query rate down
10%. Section 11 item 2 remains blocker for relative performance claims.
