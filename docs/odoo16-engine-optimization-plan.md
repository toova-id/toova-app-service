# Odoo 16 Engine Optimization Plan

> Current state and handover live in [CHANGELOG-engine-optimization.md](CHANGELOG-engine-optimization.md). This document
> is the original architecture analysis; read the changelog first to see what shipped.

**Status:** Core phases implemented; realistic client workload and risky ORM/cache phases remain open.
**Target:** Odoo 16 Community fork
**Scope:** Runtime, worker architecture, memory, CPU, HTTP, PostgreSQL coordination, cache, ORM instrumentation, and production image
**Benchmark targets:** [Odoo 16 Engine Benchmark Targets](odoo16-engine-benchmark-targets.md)
**Runtime image plan:** [Odoo 16 Runtime Image Optimization Plan](odoo16-runtime-image-optimization-plan.md)
**Implementation log:** [Odoo 16 Engine Implementation Log](odoo16-engine-implementation-log.md)

## 1. Goal

Optimize Odoo 16 source while preserving Python addon compatibility and business behavior.

Primary goals:

- Reduce idle and peak memory.
- Reduce CPU overhead and Kubernetes throttling.
- Improve p50, p95, and p99 request latency.
- Improve throughput under bounded resources.
- Prevent one overloaded component from degrading whole pod.
- Reduce PostgreSQL round-trips and connection pressure.
- Make worker lifecycle aware of container limits.
- Preserve ORM, security, transaction, compute, and addon semantics.

Expected outcome is optimized Odoo runtime, not rewritten ERP engine.

## 2. Non-goals

Initial work will not:

- Rewrite Odoo in Go.
- Replace Python ORM.
- Write directly to Odoo tables outside ORM.
- Convert synchronous ORM to asyncio or ASGI.
- Change recordset semantics.
- Change transaction isolation or commit boundaries.
- Change ACL, record-rule, company, or `sudo()` semantics.
- Change computed-field dependency behavior.
- Remove required XML, QWeb, translations, static assets, or report resources.
- Add microservices before engine bottlenecks are measured.

## 3. Current Source Findings

### 3.1 Request-level registry signaling query

Every database request calls:

```text
Request._serve_db()
  -> Registry(self.db).check_signaling()
  -> open cursor
  -> SELECT registry/cache sequence values
  -> close cursor
  -> open business cursor
```

Relevant files:

```text
odoo/http.py
odoo/modules/registry.py
```

This adds PostgreSQL pool checkout and SQL round-trip to every database request.

### 3.2 Container-unaware memory limits

Current worker memory control uses process virtual memory on Linux:

```python
return pmem.vms
```

Kubernetes enforces total pod cgroup memory. Per-process VMS does not represent pod physical usage. Odoo can consider workers healthy while Kubernetes approaches pod OOMKill.

Relevant file:

```text
odoo/service/server.py
```

### 3.3 Process-heavy prefork architecture

Production prefork can contain:

```text
master
HTTP workers
cron workers
gevent/realtime process
```

Each process carries Python runtime, registry references, local caches, and private heap pages. Many workers under sub-one-core CPU quota can increase memory and context switching without improving CPU throughput.

### 3.4 Broad ORM cache invalidation

Registry uses one shared method-cache LRU per process. Many `clear_caches()` calls clear whole registry method cache, even when one model or method changed.

Relevant files:

```text
odoo/tools/cache.py
odoo/modules/registry.py
odoo/models.py
```

This can cause cache stampedes and repeated menu, rule, view, routing, and configuration queries.

### 3.5 Long worker lifetime

Worker recycling uses fixed request limits. Fixed limits can synchronize worker restarts and allow heap fragmentation or addon leaks to accumulate between restarts.

### 3.6 Limited performance visibility

Odoo already tracks SQL count and SQL duration per request thread, but does not expose one complete low-overhead request breakdown for normal production diagnosis.

Relevant files:

```text
odoo/http.py
odoo/sql_db.py
odoo/api.py
```

## 4. Target Runtime Architecture

Current isolated deployment:

```text
Ingress
  normal HTTP/RPC ------> HTTP deployment: master + WorkerHTTP
  /websocket* ----------> realtime deployment: one gevent process
                           |
cron deployment --------> master + WorkerCron
broker deployment ------> outbox relay + optional NSQ consumer
                           |
       full model registry in every role
                           |
PostgreSQL + Redis + S3/R2 + NSQ
```

HTTP and realtime share Redis sessions. Every role uses same immutable image and full model
registry. Controllers/services are role-specific. No shared filestore PVC exists when S3 is
enabled.

Core principles:

- Preload immutable metadata before worker fork.
- Preserve copy-on-write memory as long as possible.
- Keep cache local to each worker.
- Replace per-request signaling SQL with local generation comparison.
- Use one durable event/control connection per pod.
- Bound request concurrency and queue size.
- Apply pod-level memory policy before OOMKill.
- Keep cron and realtime explicit and measurable.
- Scale worker count against CPU quota and DB budget.

## 5. Proposed Work

### Phase 0: Reproducible Baseline

Build benchmark harness before behavior-changing patches.

Workloads:

```text
login
load backend and menus
search/read partners
create partner
create quotation
add 10 order lines
confirm quotation
create invoice
post invoice
10, 25, and 50 concurrent clients
cron active
realtime active when used
```

Collect:

```text
startup-to-ready
requests per second
p50/p95/p99 latency
error rate
CPU usage
CPU throttled time
cgroup memory current/max
RSS/PSS/USS per process
DB connections
SQL count/request
SQL time/request
transaction duration
lock wait
WAL rate
worker recycle count
OOMKill count
```

Each optimization must run against same image base, database snapshot, addon set, and workload.

### Phase 1: Production Instrumentation

Add sampled, low-overhead metrics without changing business behavior.

Per request:

```text
total duration
routing duration
authentication duration
registry signaling duration
cursor checkout duration
SQL count and duration
flush count and duration
recompute count, records, and duration
ORM cache hit/miss
JSON decode/encode duration
response size
```

Runtime metrics:

```text
registry load duration
registry model and field count
method-cache entries and hit ratio
cache clear count and caller
worker inflight requests
socket backlog/queue wait
worker RSS/PSS/USS
pod cgroup memory
CPU quota and throttling
DB pool used/count/max
worker recycle reason
```

Suggested policy:

```text
normal requests: sampled
slow requests: always recorded
credentials and payload values: never logged
```

Files likely changed:

```text
odoo/http.py
odoo/sql_db.py
odoo/api.py
odoo/modules/registry.py
odoo/tools/cache.py
odoo/service/server.py
```

### Phase 2: Event-driven Registry and Cache Signaling

Keep PostgreSQL sequences as source of truth. Stop querying them on every request.

New flow:

```text
cache/registry change commits
  -> sequence increments
  -> PostgreSQL NOTIFY emitted
  -> pod listener receives event
  -> local generation updates
  -> worker compares local integer
  -> cache clears or registry reloads when generation differs
```

Reliability rules:

- `NOTIFY` provides fast delivery.
- Existing sequence values provide durable reconciliation.
- Listener reconnect reads sequence values before resuming.
- Missed notifications cannot permanently leave stale generation.
- Notification happens only after successful commit.
- Existing polling path remains temporary fallback.

PgBouncer constraint:

- ORM traffic may continue through transaction pooling.
- `LISTEN/NOTIFY` needs direct PostgreSQL connection or PgBouncer session-pool endpoint.
- Keep one event connection per pod/master, not per request.

Expected effect:

- Remove one signaling query from normal DB request path.
- Reduce PgBouncer checkout rate.
- Reduce PostgreSQL query rate.
- Improve small-request and JSON-RPC latency.

### Phase 3: Cgroup-aware Supervisor

Read container limits directly.

Cgroup v2:

```text
/sys/fs/cgroup/memory.current
/sys/fs/cgroup/memory.max
/sys/fs/cgroup/cpu.max
/sys/fs/cgroup/cpu.stat
```

Use cgroup v1 fallback where required.

Track:

```text
pod memory usage
pod memory limit
CPU quota
CPU throttled periods/time
worker RSS
worker USS
worker PSS
```

Initial pressure policy:

```text
below 75%: normal
75-82%: report pressure and stop optional warmup
82-88%: block additional worker spawning
88-92%: gracefully retire largest idle/finished worker
92-95%: reject new non-critical requests
above 95%: aggressive graceful retirement before OOMKill
```

Exact thresholds remain configurable and benchmark-driven.

Worker retirement occurs after current request where possible. Supervisor reports reason and restarts only when pressure allows.

### Phase 4: Bounded Concurrency and Admission Control

Convert hidden environment controls into first-class config.

Proposed settings:

```ini
http_max_inflight = 4
http_backlog = 64
http_queue_timeout = 2
```

Behavior:

- Reject overload before opening DB cursor.
- Return `503 Service Unavailable` with `Retry-After` when no safe capacity remains.
- Do not interrupt transaction already running.
- Stop accepting new work during graceful shutdown.
- Keep DB pool and thread/process count bounded.

Purpose:

- Prevent unbounded thread and socket buildup.
- Prevent request timeout cascades.
- Protect memory and PostgreSQL connection budget.
- Produce predictable degradation under burst traffic.

### Phase 5: Explicit Runtime Roles — Implemented

Implemented selector:

```ini
runtime_role = all | http | realtime | cron | broker
```

HTTP no longer starts realtime/gevent child. Realtime runs dedicated gevent process; cron
and broker run dedicated non-HTTP processes. `all` remains compatibility mode.

Rules:

- Deploy realtime when Discuss, live chat, websocket, or bus-dependent behavior is required.
- Route `/websocket*` only to realtime port `8072`.
- Keep cron concurrency independently bounded.
- Broker requires exactly one configured database.
- Calculate DB connections across every process and replica; `db_maxconn` is per process.

Provide runtime profiles:

#### Compact

For CPU quota around one core or less:

```text
single process
bounded HTTP threads
one registry heap
cron concurrency one
realtime optional
```

#### Lean prefork

For isolation with small resource budget:

```text
master
one or two HTTP workers
one cron worker
realtime optional
```

#### Throughput prefork

For larger CPU and DB budget:

```text
worker count based on measured workload
separate cron/realtime roles when useful
strict total DB connection budget
```

Runtime logs recommendation when configured process count greatly exceeds cgroup CPU quota. It does not silently rewrite operator config.

### Phase 6: Copy-on-write Preservation

Odoo already preloads registries before forking. Improve preservation:

```text
load modules and registries
warm safe immutable metadata
gc.collect()
gc.freeze()
close inherited DB pools
fork workers
```

Make feature opt-in first:

```ini
prefork_gc_freeze = True
```

On registry reload/module upgrade:

```text
gc.unfreeze()
reload registry
gc.collect()
gc.freeze()
```

Measure PSS, not summed RSS, because shared pages appear in every worker RSS.

Safe prewarm candidates:

- manifest metadata;
- model and field metadata;
- compute dependency graph;
- immutable method dispatch metadata;
- routing metadata independent of user/company/context.

Do not prewarm recordsets, cursors, user data, company-specific data, or request context.

### Phase 7: Worker Lifecycle and Allocator Control

Add randomized recycling:

```ini
limit_request = 5000
limit_request_jitter = 1000
worker_max_age = 0
```

Each worker receives different effective request limit. This avoids synchronized restart.

Recycle reasons:

```text
request limit
worker USS limit
pod memory pressure
registry reload
maximum age
operator signal
```

Allocator tuning candidates:

```text
MALLOC_ARENA_MAX=2
MALLOC_TRIM_THRESHOLD_=131072
MALLOC_MMAP_THRESHOLD_=131072
```

Optional `malloc_trim(0)` only:

- after unusually large requests;
- after large cache invalidation;
- while idle under memory pressure.

Do not trim after every request because CPU cost and allocator cache loss may exceed memory benefit.

### Phase 8: Targeted ORM Method-cache Invalidation

First instrument global clears. Then add narrower invalidation.

New capabilities:

```text
clear one cached method
clear one model namespace
clear one cache category
clear all as compatibility fallback
```

Potential namespaces:

```text
configuration
security rules
users/groups
menus/actions
views/QWeb
routing
assets
translations
```

Cross-worker event includes namespace and generation. Worker clears only affected entries.

Global clear remains mandatory for:

- module install/update/uninstall;
- unknown dependencies;
- registry rebuild;
- explicit compatibility fallback.

This phase carries higher correctness risk and starts only after invalidation callers are mapped by instrumentation.

### Phase 9: Request Hot-path Optimization

Candidates require benchmark proof.

#### JSON input

Current path decodes request bytes to text before `json.loads()`. Test direct bytes parsing to remove one temporary allocation.

#### JSON output

Measure serialization cost and payload memory before changing encoder. Optional faster serializer must preserve:

- Unicode behavior;
- date/time conversion;
- float behavior;
- error format;
- security escaping;
- existing API contract.

No new JSON dependency unless benchmark shows material gain.

#### RPC dispatch metadata

Precompute safe public method dispatch metadata during registry setup:

```text
(model, method)
  -> callable
  -> API mode
  -> remote visibility
```

Avoid repeated MRO/private-method inspection for small RPC calls. Registry reload rebuilds map. Dynamic methods retain fallback path.

### Phase 10: ORM Hot-path Optimization

Modify ORM only from measured evidence.

Investigate:

```text
N+1 query patterns
recompute storms
small compute batches
redundant flushes
over-prefetch
record-rule compilation
single-record create overrides
large binary/base64 reads
cache invalidation storms
```

Rules:

- Prefer batch ORM operations.
- Preserve transaction and recompute semantics.
- Do not globally reduce prefetch size without query/memory evidence.
- Do not remove `flush_all()` calls without transaction regression tests.
- Warn when hot models override `create()` without `@api.model_create_multi`.
- Add indexes only from production query evidence.

Likely large gains will come from specific hot business modules, not generic Python micro-optimizations.

### Phase 11: Static, Asset, and Binary Path

Production design should avoid using ORM workers for static transfer.

Offload where safe:

```text
/<module>/static/*
/web/assets/*
immutable public resources
```

Use reverse proxy/CDN cache for hashed assets.

Avoid binary/base64 fields in generic list APIs. Serve large binaries through dedicated binary route or object storage integration when required.

Source may export static manifest metadata during build/startup to avoid repeated filesystem discovery.

### Phase 12: Python Runtime and Image

Benchmark supported runtimes using identical workload:

```text
Python 3.10
Python 3.11
Python 3.12
```

Validate:

```text
gevent
greenlet
psycopg2
lxml
Pillow
reportlab
Enterprise addons
custom addons
```

Do not migrate to psycopg3 or asynchronous ORM in initial optimization.

Production image plan:

```text
multi-stage wheel build
runtime-only OS libraries
no compiler or headers in final image
no package-manager caches
no pip cache
precompiled Python bytecode
non-root runtime
immutable source
read-only root filesystem where possible
```

Image size optimization improves pull, rollout, disk, and attack surface. It is not expected to materially reduce steady-state ORM memory by itself.

## 6. PostgreSQL and PgBouncer Requirements

Engine optimization cannot ignore database behavior.

Track:

```text
DB CPU
active and waiting connections
transaction duration
lock wait
serialization retries
deadlocks
WAL bytes/second
buffer cache hit ratio
temporary file usage
autovacuum lag
slow query fingerprints
```

Connection planning formula:

```text
total potential client connections =
    pod replicas
  x process-local pool count
  x db_maxconn
```

PgBouncer reduces PostgreSQL backend connections but does not make unlimited Odoo client connections free.

Use separate connection behavior:

```text
ORM transaction traffic -> PgBouncer transaction pool
event LISTEN/NOTIFY      -> direct PostgreSQL or session pool
```

## 7. Validation and Compatibility

Every engine patch requires before/after benchmark and regression test.

Minimum suites:

```text
core/base
web
sale
account
stock
mail
bus when realtime enabled
module install/update/uninstall
multiprocess cache invalidation
multi-company security
serialization/deadlock retry
HTTP and JSON-RPC
```

Additional failure tests:

```text
lost PostgreSQL notification
listener reconnect
PgBouncer restart
worker killed during request
worker graceful retirement
pod memory pressure
queue/backlog saturation
registry reload
rolling deployment
cron overlap
```

Correctness wins over benchmark. Optimization with inconsistent accounting, stock, permissions, or cache state is rejected.

## 8. Success Criteria

Final targets must be fixed after baseline. Initial direction:

```text
No regression in business behavior or security
No lost cache/registry invalidation
Lower SQL requests for small endpoints
Lower pod PSS at equivalent concurrency
Lower peak memory and no avoidable OOMKill
Lower CPU throttled time
Better p95/p99 during burst
Bounded DB connections
Predictable 503 overload behavior
Stable worker recycling without restart waves
```

Reasonable hypotheses, not commitments:

```text
small request latency/DB overhead: 10-30% lower
prefork PSS:                       15-35% lower
runtime overhead CPU:             10-30% lower
write-heavy business methods:      0-15% engine-only gain
peak stability:                   materially improved
```

Write operations may improve much more only where profiling finds N+1 queries, broad recompute dependencies, excessive flushes, missing indexes, or inefficient custom addon code.

## 9. Implementation Status and Remaining Order

Implemented:

```text
production-safe instrumentation
event signaling plus reconciliation and poll fallback
cgroup-aware resource reporting and pressure response
HTTP, realtime, cron, and broker role isolation
copy-on-write gc.freeze option
recycle jitter, worker age, and memory-pressure retirement
Redis sessions, S3/R2 attachments, native NSQ broker
role-aware core controller imports and lazy optional libraries
multi-replica/failure/storage audit harnesses
```

Remaining order:

1. Run representative client workload and baseline/candidate comparison.
2. Validate production PgBouncer/direct signaling and Redis failover topology.
3. Soak R2 timeout/throttling/large-range/credential rotation and define backup RPO/RTO.
4. Add manifest-based controller/runtime components only if custom addon footprint warrants it.
5. Instrument global cache-clear callers and retry targeted invalidation only behind ACL gates.
6. Optimize ORM/query/recompute paths only from production profiler evidence.
7. Re-run Community/Enterprise/custom addon install-update gate after every loader change.

## 10. First Deliverable

First source milestone should contain only:

```text
benchmark harness
request and SQL metrics
cgroup CPU/memory metrics
worker PSS/USS metrics
startup capacity report
no ORM semantic changes
```

Second milestone:

```text
event-driven signaling
sequence reconciliation
fallback polling
listener failure tests
before/after benchmark report
```

This ordering gives trustworthy measurements before risky engine changes.

## 11. Security Note

Production master password shown during planning must be rotated. Store replacement in Kubernetes Secret and inject it during Helm rendering. Do not commit plaintext credentials to repository or values files.
