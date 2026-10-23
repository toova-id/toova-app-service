# Target Benchmark Optimasi Engine Odoo 16

> Hasil pengukuran terbaru ada di [CHANGELOG-engine-optimization.md](CHANGELOG-engine-optimization.md).
> Target di dokumen ini belum terbukti; baseline pembanding belum dibuat.

**Status:** Target gates remain proposed; role-import footprint has measured before/after results.
**Target:** Fork Odoo 16 Community
**Dokumen induk:** [Odoo 16 Engine Optimization Plan](odoo16-engine-optimization-plan.md)

## 1. Tujuan Benchmark

Benchmark membuktikan bahwa perubahan source menghasilkan Odoo yang lebih cepat, lebih hemat resource, dan lebih stabil tanpa mengubah behavior bisnis.

Perbandingan wajib memakai kondisi sama:

```text
source before vs source after
resource CPU sama
resource memory sama
jumlah replica sama
snapshot database sama
addon terpasang sama
konfigurasi PostgreSQL/PgBouncer sama
workload dan concurrency sama
```

Resource referensi production saat ini:

```text
CPU limit:     940m
Memory limit:  2200Mi
HTTP workers:  3
Cron workers:  1
```

Angka production ini menjadi profil benchmark pertama. Profil tambahan boleh dibuat setelah baseline pertama selesai.

## 2. Definisi Keberhasilan

### 2.1 Target committed

Target minimum agar fork dinilai berhasil:

| Metrik | Target sesudah optimasi |
|---|---:|
| Idle pod memory | Turun minimal 20% |
| Peak pod memory | Turun minimal 20% |
| Common request p95 | Turun minimal 20% |
| Write request p95 | Turun minimal 15% |
| Throughput pada resource sama | Naik minimal 20% |
| CPU time per request | Turun minimal 15% |
| PostgreSQL query rate normal | Turun minimal 10% |
| Signaling query per DB request | Turun dari 1 menjadi 0 pada steady-state |
| OOMKill saat stress test | 0 |
| DB pool exhaustion | 0 |
| Request hilang saat recycle | 0 |
| Functional regression | 0 |
| Security regression | 0 |

### 2.2 Target stretch

Target bagus jika profiling menemukan hot path besar:

| Metrik | Target stretch |
|---|---:|
| Idle pod memory | Turun 30–40% |
| Peak pod memory | Turun 30–40% |
| Common request p95 | Turun 30–50% |
| Write request p95 | Turun 25–40% |
| Throughput | Naik 35–60% |
| CPU time per request | Turun 25–35% |
| PostgreSQL query rate | Turun 20–35% |
| Startup-to-ready | Turun 25–40% |

Target stretch bukan janji. Hasil tersebut memerlukan temuan seperti:

```text
N+1 query
recompute storm
redundant flush
cache invalidation storm
index yang hilang
single-record create pada hot path
```

### 2.3 Batas klaim

Target global awal:

```text
20–40% improvement dengan resource sama
```

Target berikut tidak boleh dijanjikan sebelum baseline dan profiler membuktikannya:

```text
2x lebih cepat secara global
50% lebih hemat memory secara global
```

Peningkatan sebesar itu mungkin hanya pada endpoint tertentu yang punya defect performa besar.

## 3. Benchmark Gate

Setiap perubahan harus melewati empat gate:

```text
1. Correctness
2. Resource
3. Performance
4. Overload stability
```

Patch ditolak jika:

- lebih cepat tetapi menghasilkan behavior berbeda;
- memory turun tetapi query atau latency memburuk melebihi batas;
- throughput naik tetapi lock contention atau deadlock meningkat;
- happy path cepat tetapi pod OOM saat burst;
- benchmark tidak reproducible;
- hasil hanya berasal dari perubahan resource/config yang tidak setara.

## 4. Metrik Memory

### 4.1 Metrik utama

Gunakan:

```text
container_memory_working_set_bytes
cgroup memory.current
cgroup memory.max
total process PSS
worker USS
worker RSS sebagai diagnostic
```

Jangan menjumlahkan RSS semua prefork worker sebagai total memory utama. Shared page dihitung pada setiap RSS. PSS membagi shared page secara proporsional; USS menunjukkan memory unik process.

### 4.2 Target terhadap pod 2200Mi

Target operasional awal:

```text
normal steady-state:  <= 1500Mi
normal peak:          <= 1750Mi
stress peak:          <= 1900Mi
OOMKill:              0
```

Interpretasi:

```text
1500Mi / 2200Mi = 68% pod limit
1750Mi / 2200Mi = 80% pod limit
1900Mi / 2200Mi = 86% pod limit
```

Headroom diperlukan untuk:

- request besar;
- cache growth;
- cron;
- report generation;
- worker replacement overlap;
- temporary Python allocation;
- graceful shutdown.

Target absolut akan dikoreksi setelah baseline aktual tersedia. Target relatif minimal 20% tetap menjadi gate utama.

### 4.3 Memory stability test

Jalankan minimal 20.000 request setelah warmup.

Bandingkan:

```text
memory pada request 5.000
memory pada request 10.000
memory pada request 20.000
```

Pass jika salah satu berlaku:

```text
memory growth setelah warmup <= 10%
```

atau:

```text
worker recycle mengembalikan memory ke level sehat
tanpa outage, request hilang, atau restart serentak
```

## 5. Metrik CPU

CPU limit referensi:

```text
940m = 0,94 CPU core
```

Resource tidak dinaikkan selama perbandingan before/after.

Target:

| Metrik | Target |
|---|---:|
| CPU time/common request | Turun minimal 15% |
| CPU time/write transaction | Turun minimal 10% |
| Context switching | Turun minimal 20% |
| CPU throttled wall time saat normal load | Kurang dari 5% |
| CPU throttled wall time saat target peak | Kurang dari 15% |
| Throughput pada 940m | Naik minimal 20% |

Efisiensi utama dihitung dengan:

```text
completed requests / CPU-seconds
```

Contoh format, bukan baseline aktual:

```text
Before: 8 request/second pada 900m CPU
After:  10 request/second pada <= 900m CPU
Stretch: 12 request/second pada <= 900m CPU
```

## 6. Metrik Latency

### 6.1 Common UI dan RPC

Workload:

```text
session/authentication
load menus
fields_get
name_search
search_read res.partner
search_read sale.order
read satu record
```

Target:

| Percentile | Committed | Stretch |
|---|---:|---:|
| p50 | Turun minimal 15% | Turun 25–35% |
| p95 | Turun minimal 20% | Turun 30–50% |
| p99 | Turun minimal 20% | Turun 30–45% |

### 6.2 Write ringan

Workload:

```text
create res.partner
update res.partner
create product sederhana
update chatter sederhana
```

Target:

| Percentile | Committed | Stretch |
|---|---:|---:|
| p50 | Turun minimal 10% | Turun 20–30% |
| p95 | Turun minimal 15% | Turun 25–40% |
| p99 | Turun minimal 15% | Turun 25–35% |

### 6.3 Write berat

Workload:

```text
create sale order dengan 10 lines
confirm sale order
create invoice
post invoice
validate stock picking
```

Target:

| Percentile | Committed | Stretch |
|---|---:|---:|
| p50 | Turun minimal 5% | Turun 15–25% |
| p95 | Turun minimal 10–15% | Turun 20–35% |
| p99 | Turun minimal 10% | Turun 20–30% |

Write berat punya target lebih rendah karena sering didominasi business logic, PostgreSQL, lock, stored compute, mail, stock, dan accounting.

## 7. Metrik SQL dan PostgreSQL

### 7.1 Registry/cache signaling

Baseline source:

```text
setiap DB request menjalankan minimal satu query signaling tambahan
```

Target:

```text
normal steady-state: 0 signaling query/request
```

Sequence reconciliation hanya berjalan saat:

```text
listener startup
listener reconnect
generation mismatch
periodic safety reconciliation
```

### 7.2 SQL per request

| Workload | Target |
|---|---:|
| Request ringan | Turun minimal 10% |
| Read umum | Turun 5–15% |
| Write ringan | Turun 5–15% |
| Write berat | Turun 5–20% |
| Endpoint dengan N+1 | Turun 30–80% |

Contoh format, bukan angka target final:

```text
search_read sale.order
  before: 12 query
  after:   8–10 query

create sale order dengan 10 lines
  before: 180 query
  after:  140–165 query

confirm sale order
  before: 250 query
  after:  210–235 query
```

Angka absolut dikunci setelah baseline.

### 7.3 Connection dan transaction

Target:

```text
active DB connections normal: turun minimal 20%
connection checkout p95: turun minimal 20%
pool exhaustion: 0
control/event connection: 1 per pod/master
transaction duration p95 write: turun minimal 10%
lock wait p95: tidak lebih buruk dari baseline
deadlock standard benchmark: 0
serialization retry: tidak naik
```

Optimasi ditolak jika throughput aplikasi naik tetapi DB lock contention memburuk.

## 8. Metrik Cache

Setelah warmup:

```text
ormcache aggregate hit ratio target: >= 90%
stretch: >= 95%
```

Hit ratio tetap dianalisis per method. Tidak semua cache punya pola penggunaan sama.

Target invalidation:

```text
global cache clear turun minimal 80% pada operasi konfigurasi normal
targeted invalidation hanya membersihkan namespace terkait
cache rebuild SQL turun minimal 50%
cache stampede tidak terjadi
stale cache regression = 0
```

Correctness lebih penting dari cache hit ratio. Security rule, permission, atau view yang berisiko stale tetap memakai global invalidation.

## 9. Startup Benchmark

Ukur:

```text
process start
-> config parsed
-> Python modules loaded
-> registry ready
-> readiness endpoint sukses
```

Target:

| Metrik | Committed | Stretch |
|---|---:|---:|
| Startup-to-ready | Turun minimal 15% | Turun 25–40% |
| Registry load time | Tidak memburuk | Turun minimal 20% |
| Peak startup memory | Turun minimal 15% | Turun minimal 30% |

Cold dan warm startup dipisahkan:

```text
cold: image/filesystem/page cache belum hangat
warm: image dan filesystem cache tersedia
```

## 10. Overload Benchmark

Naikkan concurrency bertahap:

```text
1 -> 5 -> 10 -> 25 -> 50 -> 100
```

Tambahkan burst:

```text
1.000 request dalam waktu singkat
```

Target behavior ketika kapasitas penuh:

```text
request aktif tetap selesai
request berlebih ditolak cepat
503 membawa Retry-After
memory tetap di bawah batas stress
DB pool tidak habis
pod tidak restart
service pulih otomatis setelah traffic turun
```

Target:

| Metrik | Target |
|---|---:|
| OOMKill | 0 |
| Pod restart | 0 |
| DB pool exhaustion | 0 |
| Overload rejection latency | Kurang dari 500ms |
| Recovery setelah load turun | Kurang dari 30 detik |
| Stress peak memory | Kurang dari 1900Mi pada profil referensi |
| Existing request corruption | 0 |
| Partial transaction | 0 |

Error rate boleh naik melalui deliberate `503`. Timeout panjang, OOM, partial transaction, atau pod restart tidak boleh terjadi.

## 11. Worker Lifecycle Benchmark

Test:

```text
request-limit recycle
memory-pressure recycle
registry reload
SIGTERM saat traffic aktif
replacement worker saat memory mendekati limit
```

Pass criteria:

```text
lost transaction: 0
corrupt response: 0
synchronized worker restart: 0
traffic blackout: 0 jika worker lain tersedia
worker menyelesaikan request sebelum exit
replacement worker hanya spawn jika memory budget cukup
```

Target graceful shutdown:

```text
<= 30 detik untuk request normal
```

## 12. Correctness Gate

Behavior berikut wajib tetap sama:

```text
recordset result
computed fields
Python dan SQL constraints
ACL
record rules
multi-company access
sudo behavior
mail tracking
stock reservation
accounting entries
transaction rollback
serialization retry
module install/update/uninstall
HTTP dan JSON-RPC contract
```

Target:

```text
upstream test regression: 0
security regression: 0
data mismatch: 0
lost committed write: 0
duplicate business write: 0
```

Minimum test suites:

```text
base/core
web
sale
account
stock
mail
bus jika realtime aktif
module install/update/uninstall
multiprocess cache invalidation
multi-company security
serialization/deadlock retry
HTTP/JSON-RPC
```

## 13. Benchmark Matrix

### 13.1 Cold single request

Mengukur:

```text
startup
first registry access
first routing/cache build
```

### 13.2 Warm single concurrency

Mengukur:

```text
raw endpoint latency
SQL count
CPU/request
allocation/request
```

### 13.3 Warm target concurrency

Untuk profil referensi 940m CPU:

```text
concurrency 5
concurrency 10
concurrency 25
```

Mengukur:

```text
throughput
p95/p99
DB pool behavior
worker utilization
```

### 13.4 Overload

```text
concurrency 50
concurrency 100
burst 1.000 request
```

Mengukur:

```text
backpressure
memory containment
503 behavior
recovery
```

### 13.5 Durasi dan pengulangan

Setiap scenario:

```text
warmup:       2–5 menit
measurement:  10–15 menit
repetition:   minimal 5 kali
```

Gunakan median lima run. Simpan distribusi p50/p95/p99, bukan hanya average.

## 14. Target Per Fase Implementasi

### Fase instrumentation

```text
performance overhead instrumentation < 2%
metric completeness = 100%
payload atau credential leakage = 0
business behavior change = 0
```

### Fase event-driven signaling

```text
signaling SQL/request: 1 -> 0
common RPC p95: turun 5–20%
DB query rate: turun 5–15%
write berat: turun 0–5%
```

### Fase cgroup supervisor dan admission control

```text
OOMKill saat stress: 0
stress peak memory: < 1900Mi pada profil referensi
overload rejection: < 500ms
recovery: < 30 detik
```

Happy-path latency boleh hampir sama. Nilai utama fase ini ialah stability.

### Fase copy-on-write dan worker lifecycle

```text
pod memory: turun 15–30%
total process PSS: turun 15–35%
memory slope setelah warmup: stabil
synchronized recycle: 0
```

### Fase targeted cache invalidation

```text
global invalidation: turun minimal 80%
cache rebuild SQL: turun minimal 50%
warm request p95: turun 5–15%
stale cache regression: 0
```

### Fase ORM hot-path optimization

```text
write p95: turun 15–35%
SQL/write: turun 10–40%
throughput: naik 20–50%
```

Hasil tergantung temuan profiler pada addon dan workflow produksi.

## 15. Format Laporan Before/After

Gunakan template berikut untuk setiap benchmark milestone:

```text
Environment
-----------
Git revision before:
Git revision after:
Python version:
Database snapshot:
Installed modules hash:
CPU request/limit:
Memory request/limit:
HTTP workers:
Cron workers:
Realtime enabled:
PgBouncer mode:
Concurrent users:
Warmup duration:
Measurement duration:
Repetition count:
```

```text
Metric                         Before       After       Change     Gate
------------------------------------------------------------------------
Idle pod memory
Peak pod memory
Total process PSS
Largest worker USS
CPU/request
Throughput
Common RPC p50
Common RPC p95
Common RPC p99
Create sale order p95
Confirm sale order p95
SQL/common request
SQL/write request
PostgreSQL query rate
DB connections p95
Transaction duration p95
Lock wait p95
CPU throttled wall time
OOMKill during burst
Overload rejection latency
Overload recovery
Functional regressions
Security regressions
```

Contoh hasil hipotetis:

```text
Metric                         Before       After       Change
----------------------------------------------------------------
Idle pod memory                1680Mi       1290Mi      -23.2%
Peak pod memory                2105Mi       1690Mi      -19.7%
Total process PSS              1720Mi       1300Mi      -24.4%
CPU/request                    84ms         68ms        -19.0%
Throughput                     8.2rps       10.4rps     +26.8%
Common RPC p50                 120ms        94ms        -21.7%
Common RPC p95                 390ms        275ms       -29.5%
Common RPC p99                 780ms        540ms       -30.8%
Create sale order p95          1100ms       890ms       -19.1%
Confirm sale order p95         1850ms       1600ms      -13.5%
SQL/common request             14           11          -21.4%
PostgreSQL query rate          720/s        590/s       -18.1%
DB connections p95             14           10          -28.6%
CPU throttled wall time        18%          7%          -11pp
OOMKill during burst           2            0
Overload recovery              restart      18s
Functional regressions         0            0
Security regressions           0            0
```

Angka contoh bukan prediksi. Format ini menunjukkan cara hasil final akan dibaca.

## 16. Aturan Interpretasi

### Improvement valid

```text
resource sama
correctness sama
hasil konsisten pada minimal lima run
median membaik
p95/p99 tidak mengalami regresi tersembunyi
DB pressure tidak dipindahkan menjadi lock contention
```

### Improvement tidak valid

```text
CPU atau memory limit after lebih besar
jumlah replica after lebih banyak
cache before cold tetapi after warm
snapshot data berbeda
addon set berbeda
error/503 dibuang dari perhitungan throughput
hasil hanya satu run
average membaik tetapi p99 rusak berat
```

### Trade-off yang masih dapat diterima

Contoh:

```text
throughput naik 25%
p95 turun 20%
CPU/request turun 18%
memory naik 2%
```

Dapat diterima jika memory tetap jauh di bawah budget dan kenaikan konsisten.

Trade-off ditolak jika salah satu gate keras gagal:

```text
correctness
security
OOM safety
transaction integrity
```

## 16.1 Measured role-import milestone

Same image base, disposable PostgreSQL database, and installed addon set:
`base`, `web`, `bus`, `base_import`, `auth_totp`, `web_editor`, `web_tour`,
`web_kanban_gauge`.

```text
role       old RSS   new RSS   change    old modules  new modules  controllers after
HTTP       99.5MiB   87.9MiB   -11.7%    1066         951          29
cron       99.6MiB   86.4MiB   -13.3%    1066         913           0
broker    100.3MiB   86.3MiB   -14.0%    1066         913           0
realtime  100.5MiB   86.2MiB   -14.2%    1066         916           3
```

Cold import milestone:

```text
import odoo RSS       76.4MiB -> 72.5MiB (-5.1%)
Python modules        796 -> 758
PyPDF2 modules         30 -> 0
```

This proves loader/import reduction only. It does not prove global throughput or production
pod-memory targets. Client addons may import controllers or heavy libraries on model load.
Reproduce with `scripts/benchmark_role_imports.py` and record image digest, database addon
set, architecture, and cold/warm state.

## 17. Final Acceptance Criteria

Fork dinyatakan berhasil ketika benchmark resource setara menunjukkan:

```text
pod memory working set turun minimal 20%
common request p95 turun minimal 20%
write request p95 turun minimal 15%
throughput naik minimal 20%
CPU/request turun minimal 15%
normal PostgreSQL query rate turun minimal 10%
steady-state signaling query/request menjadi 0
stress test menghasilkan 0 OOMKill
DB pool exhaustion 0
functional regression 0
security regression 0
```

Stretch result:

```text
memory turun 30–40%
common p95 turun 30–50%
write p95 turun 25–40%
throughput naik 35–60%
```

Benchmark final menjadi dasar penyesuaian konfigurasi production, worker count, resource request/limit, dan image. Config tidak dipakai untuk menyamarkan regresi source.