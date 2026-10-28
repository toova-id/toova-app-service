[![Build Status](https://github.com/alner-repository/alner-odoo-engine/actions/workflows/build-engine.yml/badge.svg?branch=master)](https://github.com/alner-repository/alner-odoo-engine/actions/workflows/build-engine.yml)
[![Build Status](https://github.com/alner-repository/alner-odoo-engine/actions/workflows/build-engine.yml/badge.svg?branch=feat)](https://github.com/alner-repository/alner-odoo-engine/actions/workflows/build-engine.yml)
[![Role Isolation](https://img.shields.io/badge/runtime-4%20isolated%20roles-blue)](docs/runtime-roles-storage-operations.md)
[![License](https://img.shields.io/badge/license-LGPLv3-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-16.0-informational)](https://www.odoo.com/documentation/16.0)

Odoo 16 Engine — Optimized
==========================

Extensible Odoo 16 Community engine base image. Client repositories inherit immutable releases, add private addons/dependencies, and run isolated HTTP/realtime, cron, or broker roles from identical engine source.

Verified Engine Milestones
--------------------------

| Change | Before | Current | Scope |
|---|---:|---:|---|
| Cold `import odoo` RSS | 76.4MiB | 72.5MiB | same Docker base |
| Cold imported modules | 796 | 758 | PyPDF2 deferred |
| Cron registry RSS | 99.6MiB | 86.4MiB | eight-addon disposable DB |
| Broker registry RSS | 100.3MiB | 86.3MiB | eight-addon disposable DB |
| Realtime registry RSS | 100.5MiB | 86.2MiB | eight-addon disposable DB |
| Signaling query/request | 1 poll | 0 steady-state | `registry_signaling=event` |

Role-import figures prove bootstrap reduction, not global application throughput. Historical
stress and workload benchmarks use different topologies; full context and limits live in
[engine changelog](docs/CHANGELOG-engine-optimization.md). Representative client workload
before/after remains production gate.

Base Image Contract
-------------------

```dockerfile
FROM ghcr.io/alner-repository/alner-odoo-engine:<immutable-tag>
COPY --chown=odoo:odoo addons/ /mnt/extra-addons/
```

- Odoo framework: `/opt/odoo/src/odoo`
- Built-in Community addons: `/opt/odoo/src/addons`
- Managed product addons: `/opt/odoo/managed`
- Client addons: `/mnt/extra-addons`
- Runtime config: `/etc/odoo/odoo.conf`
- Local data/scratch: `/var/lib/odoo`; persistent only when filesystem backend is deliberately used
- Stateless production attachments: S3/R2; no shared filestore PVC
- Default locales: Indonesian (`id`, loaded as `id_ID`) and source English (`en_US`)
- Pin immutable tag or digest; avoid `latest`

See [docker/README.md](docker/README.md) for dependency installation and downstream image example.

Architecture
------------
- **Multi-stage Docker build** — wheels, node-builder, runtime stages
- **Four isolated roles** — HTTP, realtime/WebSocket, cron, broker
- **Role-aware imports** — full ORM registry everywhere; controllers only where served
- **Lazy heavy libraries** — PDF, OpenSSL/cryptography, docutils, ReportLab, wkhtmltopdf
- **Registry signaling event mode** — LISTEN/NOTIFY plus durable reconciliation
- **Stateless scaling** — S3/R2 attachments and Redis HTTP/realtime sessions; no shared PVC
- **Native broker** — transactional outbox/inbox, trusted Python handlers, NSQ TCP transport
- **Storage integrity CLI** — read-only missing/unavailable/orphan reporting

Runtime benchmark
-----------------

Latest role-aware registry footprint with same disposable database and eight installed core/web addons:

| Role | Before RSS | Current RSS | Modules | Controller modules |
|---|---:|---:|---:|---:|
| HTTP | 99.5MiB | 87.9MiB | 951 | 29 |
| Cron | 99.6MiB | 86.4MiB | 913 | 0 |
| Broker | 100.3MiB | 86.3MiB | 913 | 0 |
| Realtime | 100.5MiB | 86.2MiB | 916 | 3 |

Cold `import odoo`: `76.4MiB -> 72.5MiB`, `796 -> 758` modules, PyPDF2 not loaded.
These figures are engine footprint, not final production sizing.

Earlier Linux/arm64 workload result using real PostgreSQL, Redis, nsqd, and nsqlookupd at `150m` CPU per role:

| Role | Memory limit | Workload | Result | Peak |
|---|---:|---|---:|---:|
| HTTP | 288Mi | authenticated read, concurrency 5 | 16.13 req/s, p95 594.59ms | 268.5MiB |
| Cron | 128Mi | real scheduled-action triggers | 6.62 jobs/s, p95 182.79ms | 98.0MiB |
| Broker | 128Mi | 5,000 outbox messages to NSQ | 129.32 msg/s | 86.8MiB |

HTTP at concurrency 25 produced 2.8% timeouts. Treat `150m` as light-traffic request baseline, not burst-safe limit. Full method: [changelog](docs/CHANGELOG-engine-optimization.md#63-isolated-minimum-resource-roles).

Quick Start
-----------
### Build

Default build keeps managed ERP addon scope, `id` translation, source `en_US`, and removes test files. See [addon scope](docs/managed-erp-addon-scope.md).

```bash
# Build with BuildKit cache
docker buildx build --platform linux/amd64 \
  -f docker/Dockerfile -t odoo-16-engine .

# With local addons volume
docker buildx build --platform linux/amd64 \
  -f docker/Dockerfile -t odoo-16-engine --build-arg ODOO_STRIP_TESTS=1 .
```

### Run
```bash
# Local development
docker compose -f docker/docker-compose.test.yml up -d

# Kubernetes reference deployment; replace image digest, Secrets, host, and endpoints first
kubectl apply -f k8s/odoo-runtime-example.yaml
kubectl apply -f k8s/odoo-routing-example.yaml
```

### Test
```bash
# Health check
curl http://localhost:8069/web/health

# Run tests
docker exec docker-odoo-test-1 python /opt/odoo/odoo-bin \
  --db_host=db --db_port=5432 \
  --db_user=odoo --db_password=odoo \
  -d test_ci --test-tags='/base:TestHasGroup' --workers=0
```

### GitHub Actions
Push to `master` or `feat/**` branches triggers:
1. **Build** — amd64 image by default; arm64 available through manual `platforms` input
2. **Test** — health check, smoke tests, size check
3. **Scan** — Trivy vulnerability scan
4. **Sign** — Cosign image signing
5. **SBOM** — Software Bill of Materials

Configuration
-------------
See [runtime operations guide](docs/runtime-roles-storage-operations.md) for role commands,
health, storage audit, failure semantics, and migration safety.

```ini
[options]
# HTTP deployment; use separate commands/config overrides for other roles
runtime_role = http
workers = 1
max_cron_threads = 0
db_maxconn = 4

# HTTP role memory limits; size other deployments independently
limit_memory_soft = 167772160
limit_memory_hard = 201326592
limit_memory_metric = rss

# Registry signaling
registry_signaling = event
registry_signaling_reconcile_seconds = 60

# HTTP limits
http_max_inflight = 0
http_port = 8069
gevent_port = 8072

# Stateless HTTP replicas
attachment_store = s3
s3_bucket = private-odoo-attachments
s3_prefix = odoo
s3_region = ap-southeast-3
# Optional S3-compatible provider endpoint:
# s3_endpoint_url = https://example.r2.cloudflarestorage.com
session_store = redis
redis_url = redis://redis:6379/0

# Use one role per deployment: http | realtime | cron | broker

# Dedicated broker role only
# runtime_role = broker
broker_provider = nsq
broker_database = production
nsq_discovery = lookupd
nsqd_tcp_addresses = nsqd:4150
nsqlookupd_http_addresses = http://nsqlookupd:4161

# Performance tuning
preload_gc_freeze = True
log_performance_sample_rate = 0.01
log_performance_slow_ms = 500
```

Documentation
-------------
- [Managed ERP Product Architecture](docs/managed-erp-product-architecture.md)
- [Managed Product Catalog](docs/managed-product-catalog.md)
- [Managed ERP Development Playbook and Handoff](docs/managed-erp-development-playbook.md)
- [Managed ERP Addon Scope](docs/managed-erp-addon-scope.md)
- [Managed ERP Product Scope Review](docs/managed-erp-product-scope-review.md)
- [Runtime Roles and Object Storage Operations](docs/runtime-roles-storage-operations.md)
- [Base Image and Stateless Runtime Goal](docs/odoo16-base-runtime-goal.md)
- [Optimization Plan](docs/odoo16-engine-optimization-plan.md)
- [Benchmark Targets](docs/odoo16-engine-benchmark-targets.md)
- [Implementation Log](docs/odoo16-engine-implementation-log.md)
- [Runtime Image Optimization](docs/odoo16-runtime-image-optimization-plan.md)
- [Changelog, tests, benchmark results](docs/CHANGELOG-engine-optimization.md)

Development
-----------
### Branches
- `master` — current integration branch
- `feat/targeted-cache-invalidation` — experimental; rejected implementation must not merge without ACL/security regression proof

Use `git branch -a` for current branch inventory; old feature names are not release status.

### Building Locally
```bash
# Build image
docker compose -f docker/docker-compose.test.yml build

# Initialize database
docker compose -f docker/docker-compose.test.yml run --rm --no-deps odoo-init

# Run tests
docker compose -f docker/docker-compose.test.yml up -d
docker exec docker-odoo-test-1 python /opt/odoo/odoo-bin \
  --db_host=db --db_port=5432 \
  --db_user=odoo --db_password=odoo \
  -d test_ci --test-tags='/base:*' --workers=0
```

### Docker Compose Files
- `docker/docker-compose.test.yml` — Local test harness
- `k8s/` — GKE deployment manifests
- `docker/Dockerfile` — Multi-stage optimized Dockerfile
- `docker/odoo.conf` — Runtime configuration

License
-------
This project is licensed under the LGPLv3 License — see the [LICENSE](LICENSE) file for details.

Odoo is a suite of web based open source business apps. The main Odoo Apps include an [Open Source CRM](https://www.odoo.com/page/crm), [Website Builder](https://www.odoo.com/app/website), [eCommerce](https://www.odoo.com/app/ecommerce), [Warehouse Management](https://www.odoo.com/app/inventory), [Project Management](https://www.odoo.com/app/project), [Billing &amp; Accounting](https://www.odoo.com/app/accounting), [Point of Sale](https://www.odoo.com/app/point-of-sale-shop), [Human Resources](https://www.odoo.com/app/employees), [Marketing](https://www.odoo.com/app/social-marketing), [Manufacturing](https://www.odoo.com/app/manufacturing), and more.

Odoo Apps can be used as stand-alone applications, but they also integrate seamlessly so you get a full-featured [Open Source ERP](https://www.odoo.com) when you install several Apps.

Getting started with Odoo
-------------------------
For a standard installation please follow the [Setup instructions](https://www.odoo.com/documentation/16.0/administration/install/install.html) from the documentation.

To learn the software, we recommend the [Odoo eLearning](https://www.odoo.com/slides), or the [business game](https://www.odoo.com/page/scale-up-business-game). Developers can start with [the developer tutorials](https://www.odoo.com/documentation/16.0/developer/howtos.html).

Contributing
------------
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

Support
-------
- [Documentation](https://www.odoo.com/documentation/16.0)
- [Forum](https://www.odoo.com/forum/help-1)
- [GitHub Issues](https://github.com/alner-repository/alner-odoo-engine/issues)
