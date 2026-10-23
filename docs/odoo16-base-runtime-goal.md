# Odoo 16 Base Image and Stateless Runtime Goal

**Status:** Core implementation present; production integration and scale gates pending.

## 1. Product goal

This repository publishes an extensible Odoo 16 Community **base image**. Client repositories inherit one immutable image digest, then add private addons and optional client Python dependencies.

```dockerfile
FROM ghcr.io/alner-repository/alner-odoo-engine:<immutable-tag>

USER root
COPY --chown=odoo:odoo requirements.txt /tmp/client-requirements.txt
RUN pip install --no-cache-dir -r /tmp/client-requirements.txt \
    && rm /tmp/client-requirements.txt
COPY --chown=odoo:odoo addons/ /mnt/extra-addons/
USER odoo
```

Base contract:

```text
Odoo core                  /opt/odoo/odoo
Community runtime addons   /opt/odoo/addons
Client addons              /mnt/extra-addons
Runtime config             /etc/odoo/odoo.conf
Temporary files            /tmp
Persistent Odoo data       /var/lib/odoo when filesystem storage remains enabled
Default translations       Indonesian id (Odoo language id_ID) and source English en_US
```

Every client role must use the same client image digest. Never run HTTP, cron, broker, or migration jobs with different engine/addon revisions against the same database.

## 2. Target GKE topology

Four isolated Odoo workloads, built from one immutable image:

```text
odoo-http
  normal HTTP/RPC routes
  WorkerHTTP only; no cron or gevent child
  replicas: 1..N

odoo-realtime
  /websocket and bus endpoints on port 8072
  one gevent process; no normal HTTP worker, cron, or broker
  replicas: 1..N according to bus/session design

odoo-cron
  standard Odoo scheduled actions
  WorkerCron only; replicas: 1 initially

odoo-broker
  native broker outbox relay and optional consumer
  provider initially NSQ; replicas: 1 initially, then queue-depth scaling
```

Ingress routes `/websocket*` to realtime and every other path to HTTP. Reference:
`k8s/odoo-routing-example.yaml`.

Desired roles:

```ini
runtime_role = http
runtime_role = realtime
runtime_role = cron
runtime_role = broker
```

All roles load full installed model registry because ORM inheritance, ACL, record rules,
computed fields, cron actions, and broker handlers require it. Controller/service imports
are role-specific. HTTP must not start realtime, cron, or broker services. Realtime must not
serve normal web controllers. Cron and broker must not open HTTP listeners.

## 3. Stateless storage target

Pod-local Odoo filestore prevents safe horizontal scaling. Target shared state:

```text
attachments and generated files   S3 bucket
HTTP sessions                     Redis when HTTP has multiple replicas
business data                     PostgreSQL
broker outbox/inbox/idempotency   PostgreSQL
message transport                 NSQ initially
ORM/registry/QWeb caches          process-local; never Redis
```

### S3 attachment requirements

Use object-storage APIs, not filesystem emulation.

Implemented behavior:

```text
private objects by default
AWS SDK credential chain/workload identity; no key in odoo.conf
attachment metadata stays in PostgreSQL
content-addressed conditional writes
ACL/record-rule check before short-lived signed download redirect
image transforms remain through Odoo
generated CSS remains on Odoo origin; /web/static remains in image
post-commit delete with direct-SQL reference recheck
explicit missing/access/retryable error classes
read-only integrity and orphan-report command; no automatic orphan deletion
```

Required production policy:

```text
bucket/provider region aligned with workload needs
message payload contains attachment ID/reference, never binary content
prefix treated as immutable or migrated by verified non-destructive copy
backup/versioning/replication chosen from RPO/RTO
upload/download, PDF, email, image resize, range, deletion, outage, and restore tests
```

### Session requirements

One HTTP replica may use ephemeral filesystem sessions initially. Multiple HTTP replicas require Redis-backed sessions or temporary ingress stickiness. Redis is preferred for shared sessions because TTL is native and session traffic should not add PostgreSQL WAL/query load.

Redis is not a replacement for Odoo ORM caches.

## 4. Native broker engine

Broker subsystem belongs in core engine for lifecycle and resource isolation. Addons register business handlers; they do not create consumer threads or borrow HTTP/cron worker slots.

Provider-neutral core contract:

```python
broker.publish(topic, payload, key=None)
broker.register_handler(topic, handler)
broker.consume()
broker.ack()
broker.retry()
broker.dead_letter()
```

First provider:

```ini
broker_provider = nsq
broker_topic_prefix = production.odoo
broker_max_in_flight = 10
broker_max_retries = 5
nsq_discovery = lookupd
nsqd_tcp_addresses = nsqd-0:4150,nsqd-1:4150
nsqlookupd_http_addresses = http://lookupd-0:4161,http://lookupd-1:4161
```

Future providers such as GCP Pub/Sub must implement the same core contract without changing client handler APIs.

### Topic management

Core manages:

```text
topic and channel catalog
naming/version policy
provider bootstrap
handler binding
pause/resume state
retry and dead-letter policy
health and lag metrics
admin-only destructive operations
```

NSQ creates topics/channels through publish/subscribe activity; Odoo catalog remains source of intended topology and policy.

### Safe message execution

Broker worker loads normal Odoo registry and opens one database transaction per message.

```text
receive message
validate envelope and registered topic
check inbox/idempotency key
open ORM environment with explicit user/company/context
run registered broker handler
commit transaction
ACK message
```

On failure:

```text
rollback
retry/requeue with bounded backoff
move to dead-letter topic after retry limit
```

Do not expose arbitrary `model.method`, raw Python source, or unrestricted `ir.actions.server` execution through message payloads. Handlers use an allowlist/registry and explicit execution identity.

Envelope minimum:

```json
{
  "id": "uuid",
  "database": "client_db",
  "topic": "sale.order.process.v1",
  "version": 1,
  "created_at": "2026-10-21T10:00:00Z",
  "record_ids": [123],
  "payload": {}
}
```

### Reliable publishing

HTTP, cron, and broker handlers may publish. Business transaction and message intent must commit atomically through a PostgreSQL transactional outbox:

```text
business write + outbox row
  commit together
broker relay
  publish to NSQ
  mark outbox delivered
```

Direct publish before database commit is forbidden. NSQ is at-least-once, so inbox idempotency is mandatory.

## 5. Scaling policy

```text
odoo-http     HPA by CPU plus request rate/latency
odoo-cron     singleton initially; no HPA until overlap and lock behavior is proven
odoo-broker   singleton initially; KEDA/HPA only after subscription/channel scaling semantics pass
```

All roles need a calculated PostgreSQL connection budget. `db_maxconn` is per process, not per pod.

Measured starting resources for light engine workloads:

```text
HTTP      request 150m / 288Mi   limit 500m / 384Mi
realtime  request  25m /  64Mi   limit 150m / 128Mi
cron      request  50m /  96Mi   limit 150m / 128Mi
broker    request  50m /  64Mi   limit 150m /  96Mi
```

Latest disposable runtime after role-aware imports and functional operations:

```text
HTTP worker  about 78MiB RSS
realtime     about 71MiB container memory
cron worker  about 72MiB RSS
broker       about 66MiB container memory
```

These values used eight installed core/web addons and are footprint evidence, not final
client sizing.

These are minimum engine baselines, not universal client sizing. Heavy addons, PDF,
imports, mail, and business writes need client-database benchmarks. HTTP at sustained
`150m` CPU is throughput-limited and needs HPA before burst saturation.

Initial measured reference at `940m CPU`, `512Mi`, event signaling, authenticated read workload, concurrency 25:

```text
workers   median RPS   p95       CPU/request   memory    errors/25k
1         416          9.6ms     0.82ms        119MiB    7
2         706          54.6ms    0.88ms        144MiB    2
3         1029         74.3ms    0.96ms        159MiB    0
```

Interpretation: one worker minimizes resources and latency but has poor burst resilience; two workers are a balanced starting point; three maximize this light-read throughput but increase throttling and tail latency. Separate `150m` measurements appear in section 7; write-heavy client tests remain mandatory.

## 6. Base-image size result

Measured arm64 image:

```text
before      1,567,276,290 bytes unpacked   498,807,296 bytes gzip docker-save
after         773,199,866 bytes unpacked   304,125,884 bytes gzip docker-save
change                  -50.7%                         -39.0%
```

Current base retains:

```text
473 non-test Community addon manifests
patched wkhtmltopdf
common Community Python dependencies
RTLCSS
Indonesian translation
runtime assertions
client extension path
```

Further pruning must not weaken universal base compatibility without a separate architecture decision.

## 7. Delivery order

Implemented foundation:

```text
S3 attachment backend selected by attachment_store=s3
Redis HTTP session backend selected by session_store=redis
runtime_role=broker lifecycle isolated from HTTP and cron
provider-neutral Python handler registry and ORM publish API
broker topic/subscription management UI
transactional outbox, idempotent inbox, retry, and dead-letter state
NSQ TCP publisher/consumer with optional nsqlookupd discovery
```

Implemented validation:

```text
S3 unit and live R2 integration pass, including conditional upload and signed downloads
read-only storage audit reports metadata, unique objects, missing, unavailable, and orphans
bad credentials and dead endpoint return explicit failure with exit code 1
NSQ direct and lookupd TCP publish/consume against local containers
transactional outbox relay and graceful broker shutdown
actual cron action and actual outbox publish pass on dedicated roles
two HTTP replicas share Redis session and object storage
realtime health passes on dedicated gevent deployment
Docker Compose runs HTTP x2, realtime, cron, broker, Redis, PostgreSQL, and NSQ without PVC
HTTP/realtime/cron/broker reference manifests and websocket ingress routing exist
controller imports are absent from measured cron/broker registry processes
34 focused lazy-runtime/role regression tests pass
```

Minimum-resource local benchmark at `150m` CPU per role:

```text
HTTP    288Mi  16.13 req/s, p95 594.59ms, peak 268.5MiB, 0 errors at concurrency 5
cron    128Mi   6.62 jobs/s, p95 182.79ms, peak 98.0MiB, 0 errors
broker  128Mi 129.32 msg/s, peak 86.8MiB, 0 errors for 5000 outbox messages
```

HTTP at concurrency 25 produced 2.8% timeouts. `150m` is suitable only as light-traffic
request baseline with HPA; recommended HTTP memory limit is `384Mi`. Full method and
environment details live in `docs/CHANGELOG-engine-optimization.md`.

External production gates:

1. Benchmark representative client addons and business writes at final GKE limits.
2. Define object-storage RPO/RTO, versioning/replication, retention, and restore procedure.
3. Run Redis HA failover against selected managed Redis tier.
4. Run R2/S3 timeout, throttling, large object, PDF/video range, and credential rotation soak.
5. Validate event-signaling direct endpoint, reconnect, reconciliation, and rolling failover in production topology.
6. Install NSQ exporter/KEDA and tune queue-depth query against production metrics backend.
7. Calculate PostgreSQL connection budget from final replicas, workers, signaling sessions, and `db_maxconn`.
8. Add Pub/Sub adapter only when deployment requires it.

## 8. Acceptance gates

```text
same image digest across all roles
HTTP/cron unaffected when broker disabled
no message lost after committed business transaction
at-least-once duplicate produces one business effect
bounded retries and working DLQ
broker shutdown does not abandon an active transaction
S3 removes shared PVC requirement
storage audit reports zero missing objects before and after rollout
orphan report never deletes automatically
multi-replica HTTP preserves sessions and attachment access
realtime failure does not make normal HTTP unhealthy
no ORM/security/company-context bypass
no binary payload in NSQ
no DB pool exhaustion
HPA scale-up/down does not lose work
```
