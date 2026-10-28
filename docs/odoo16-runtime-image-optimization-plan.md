# Rencana Optimasi Runtime Image Odoo 16

> Status terkini image ada di [CHANGELOG-engine-optimization.md](CHANGELOG-engine-optimization.md) bagian "Open work".
> Ukuran image harus diukur ulang setelah Community addons ikut dibundel; angka lama tidak valid karena source addon terlewat.

**Status:** Proposed
**Target:** Fork Odoo 16 Community pada Kubernetes
**Dokumen induk:** [Odoo 16 Engine Optimization Plan](odoo16-engine-optimization-plan.md)
**Target benchmark:** [Odoo 16 Engine Benchmark Targets](odoo16-engine-benchmark-targets.md)

## 1. Tujuan

Membuat image production Odoo 16 yang:

- lebih kecil dan cepat ditarik node;
- cepat mencapai readiness;
- hanya membawa dependency runtime;
- reproducible dan mudah dipatch;
- aman dijalankan sebagai non-root;
- mendukung addon Community, Enterprise, dan custom yang dipilih;
- tidak mengorbankan PDF, asset, locale, atau DB tooling tanpa keputusan eksplisit.

Optimasi image bukan pengganti optimasi engine. Image kecil terutama memperbaiki pull, rollout, cold start, disk, dan attack surface. Penurunan steady-state RAM biasanya kecil kecuali perubahan Python runtime, process topology, allocator, atau jumlah addon yang dimuat ikut dilakukan.

## 2. Temuan Source Tree

Ukuran working tree saat analisis:

```text
working tree total:       sekitar 1.1GiB
.git:                     sekitar 168MiB
src/odoo/:                sekitar 90MiB
src/addons/:              sekitar 850MiB
translation .po/.pot:     sekitar 688MiB
Python source:            sekitar 32MiB
JavaScript source:        sekitar 41MiB
XML:                      sekitar 23MiB
images:                   sekitar 43MiB
fonts dalam source:       sekitar 14MiB
test directories:         sekitar 37MiB
```

Temuan utama:

```text
translation files adalah bagian terbesar source runtime
.git tidak boleh masuk build context atau image
compiler dan development headers tidak dibutuhkan saat runtime
semua addon belum tentu dibutuhkan satu deployment
wkhtmltopdf, fonts, dan PostgreSQL client adalah dependency besar tetapi feature-dependent
```

File upstream berikut hanya untuk package/nightly testing, bukan desain production container:

```text
setup/package.dfdebian
setup/package.dfsrc
setup/package.dffedora
```

Dockerfile production sekarang berada di `docker/Dockerfile` dan menjadi satu-satunya definisi build.

## 3. Target Arsitektur Image

```text
Stage 1: wheel-builder
  compiler
  Python headers
  libpq/LDAP/XML/image development headers
  requirements.txt
  wheelhouse

Stage 2: runtime
  slim glibc base
  Python runtime
  runtime shared libraries
  selected fonts
  selected external binaries
  prebuilt wheels
  Odoo source runtime tree
  selected translation files
  no compiler or package cache
```

Runtime container menjalankan Odoo langsung sebagai PID 1 melalui exec-form command dari Kubernetes Deployment. Shell entrypoint tidak ditambahkan jika tidak ada initialization yang benar-benar dibutuhkan.

## 4. Base Image Strategy

### 4.1 Kandidat

Benchmark kandidat berikut menggunakan snapshot database dan workload sama:

```text
Python 3.10 + Debian slim
Python 3.11 + Debian slim
Python 3.12 + Debian slim
```

Source Odoo saat ini mendeklarasikan dukungan sampai Python 3.12 dan `requirements.txt` memiliki marker untuk Python 3.12. Enterprise dan custom addon tetap harus diuji sebelum Python 3.12 dipilih.

### 4.2 Rekomendasi awal

Gunakan Debian slim berbasis glibc. Versi Python pemenang dipilih dari benchmark, bukan asumsi.

Jangan gunakan Alpine sebagai baseline production karena:

- musl mengubah compatibility dan memory behavior;
- wheel binary lebih sedikit;
- build dependency lebih rumit;
- wkhtmltopdf dan library native lebih sulit;
- image kecil belum berarti runtime lebih cepat atau RAM lebih rendah.

Jangan gunakan distroless pada fase awal karena Odoo memerlukan kombinasi shared library, fonts, subprocess PDF, dan diagnosis production. Distroless dapat dievaluasi setelah dependency runtime terpetakan penuh.

### 4.3 Reproducibility

- Pin base image memakai digest pada release build.
- Build ulang berkala untuk security patch.
- Jangan menjalankan `apt-get upgrade` dalam Dockerfile.
- Install package dengan `--no-install-recommends`.
- Simpan Software Bill of Materials dan vulnerability report per image.
- Generate wheelhouse per Python version dan architecture.

## 5. Python Dependency Build

Builder menghasilkan wheel untuk seluruh dependency:

```text
pip wheel --wheel-dir=/wheelhouse -r requirements.txt
```

Runtime menginstal dari wheelhouse tanpa compiler:

```text
pip install --no-index --find-links=/wheelhouse -r requirements.txt
```

Keuntungan:

- build dependency tidak masuk final image;
- build lebih reproducible;
- runtime image lebih kecil;
- install layer lebih mudah dicache;
- tidak melakukan compile native extension saat deployment.

Dependency optional harus mengikuti feature yang dipakai:

```text
python-ldap: hanya jika LDAP dipakai
serial/USB: hanya jika hardware integration berjalan pada image sama
wkhtmltopdf: hanya jika PDF report dibuat pada deployment ini
rtlcss: hanya jika RTL asset harus dikompilasi
PostgreSQL client: hanya jika Odoo DB backup/restore command dipakai
```

Penghapusan dependency optional wajib didukung feature matrix dan smoke test. Import addon yang membutuhkan dependency hilang harus gagal saat CI, bukan saat production traffic.

## 6. Runtime OS Dependencies

Final list diturunkan dari wheel linkage dan feature matrix. Kategori umum:

```text
libpq runtime
OpenSSL runtime
libffi runtime
XML/XSLT runtime
JPEG/PNG/image runtime
LDAP/SASL runtime jika LDAP aktif
fontconfig dan selected fonts
wkhtmltopdf shared libraries jika PDF aktif
PostgreSQL client jika DB manager/backup aktif
```

Builder-only examples:

```text
build-essential
gcc
Python development headers
libpq-dev
libldap development headers
libsasl development headers
libxml2-dev
libxslt development headers
libjpeg development headers
zlib development headers
libffi development headers
```

Verifikasi final binary linkage:

```text
ldd native Python extensions
ldd wkhtmltopdf
import smoke test seluruh installed addon
```

Jangan menyalin builder shared library secara manual. Install runtime package resmi yang menyediakan SONAME terkait.

## 7. wkhtmltopdf dan Reports

Odoo 16 memakai executable `wkhtmltopdf` untuk PDF report. Paket harus memakai build patched Qt yang kompatibel dengan Odoo.

Sebelum menghapus atau mengganti:

```text
invoice PDF
sale order PDF
header/footer
internal image fetch
font rendering
barcode
multi-page table
CSS assets
```

harus lulus visual dan functional regression.

Pilihan build:

### Full report image

Membawa `wkhtmltopdf` dan font yang dibutuhkan. Ini profile default jika PDF digunakan.

### Core-only image

Tidak membawa `wkhtmltopdf`. Hanya valid jika deployment tidak pernah membuat PDF atau report dipindahkan ke role lain melalui perubahan source yang teruji.

Jangan menghapus `wkhtmltopdf` hanya demi mengecilkan image production jika user masih mencetak invoice atau laporan.

Architecture CPU harus dipastikan:

```text
linux/amd64
linux/arm64
```

Availability dan checksum binary wkhtmltopdf dapat berbeda. Multi-architecture image hanya dirilis setelah report test lulus pada setiap architecture.

## 8. Translation Pruning

Translation source sekitar 688MiB. Ini peluang pengurangan unpacked image terbesar.

Build dapat mempertahankan hanya locale yang disetujui, misalnya:

```text
id_ID/id
en_US source terms
locale bisnis lain yang aktif
.pot hanya bila dibutuhkan workflow translation
```

Policy:

```text
runtime language allowlist berasal dari build argument/release manifest
CI membaca bahasa aktif pada snapshot production
build gagal jika bahasa aktif tidak tersedia
penambahan bahasa baru memerlukan image rebuild
```

Do not prune source strings atau translation file untuk bahasa yang aktif.

Trade-off sengaja:

```text
image lebih kecil
vs
bahasa baru tidak dapat di-install tanpa image release baru
```

Pruning translation mengurangi disk/unpacked image besar. Dampak compressed image lebih kecil karena file PO mudah dikompresi. Dampak steady-state RAM hampir nol jika file tersebut tidak dimuat.

## 9. Addon Pruning

Level optimasi:

### Level 1: Safe

Pertahankan semua addon runtime. Hapus hanya:

```text
.git
GitHub metadata
source packaging helpers
Debian/RPM packaging metadata
documentation yang tidak dipakai runtime
Python/JS test directories
test-only addons yang teridentifikasi
coverage dan build artifacts
cache files
```

### Level 2: Selected addon set

Copy hanya:

```text
installed modules
dependency closure
server-wide modules
auto-install modules yang relevan
module yang disiapkan untuk install berikutnya
Enterprise/custom dependency closure
```

Dependency closure harus dibangun dari manifest, bukan daftar manual.

Risiko:

- module baru tidak dapat di-install tanpa image baru;
- hidden/auto-install dependency dapat terlewat;
- custom addon dapat melakukan dynamic lookup;
- module update membutuhkan source module tetap tersedia.

Rekomendasi: mulai Level 1. Level 2 hanya setelah build tool dependency closure dan CI module install/update tersedia.

## 10. Build Context dan Layering

`.dockerignore` minimum:

```text
.git
.github
.tx
doc
debian
setup/win32
**/__pycache__
**/*.pyc
**/*.pyo
**/.pytest_cache
**/.coverage
```

Test directory dapat diabaikan hanya pada target runtime, bukan target CI.

Layer order:

```text
1. base + runtime OS packages
2. requirements.txt + wheel install
3. stable Odoo core source
4. Community addons
5. Enterprise addons
6. custom addons
```

Jika custom addon berubah, dependency dan core layer tetap reusable.

Gunakan BuildKit cache mounts pada builder untuk apt dan pip download. Cache mount tidak masuk final image.

Final stage membersihkan:

```text
/var/lib/apt/lists/*
/root/.cache
pip cache
compiler output di luar wheelhouse
temporary build files
```

## 11. Python Bytecode

Precompile Python bytecode pada build untuk mengurangi write saat startup dan mendukung read-only root filesystem:

```text
python -m compileall -q <runtime-source>
```

Lalu runtime:

```text
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

Jangan set:

```text
PYTHONOPTIMIZE=1
python -O
```

Odoo memakai `assert` pada sejumlah invariant internal. Menghapus assert dapat mengubah behavior dan menutupi bug.

Bytecode menambah ukuran image. Pertahankan hanya jika cold-start benchmark membuktikan manfaat yang layak.

## 12. Runtime Environment

Baseline environment candidates:

```text
LANG=C.UTF-8
LC_ALL=C.UTF-8
TZ=UTC
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
PIP_DISABLE_PIP_VERSION_CHECK=1
MALLOC_ARENA_MAX=2
```

Allocator candidates berikut harus A/B benchmark dahulu:

```text
MALLOC_TRIM_THRESHOLD_
MALLOC_MMAP_THRESHOLD_
```

Jangan set `PYTHONMALLOC=malloc` atau mengganti allocator tanpa allocation, CPU, RSS/PSS, dan fragmentation benchmark.

## 13. Kubernetes Runtime Security

Target pod security context:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
  seccompProfile:
    type: RuntimeDefault
```

Gunakan fixed UID/GID pada image dan volume.

Writable paths:

```text
/var/lib/odoo
/tmp
optional runtime/cache directory yang terverifikasi
```

Target akhir:

```yaml
readOnlyRootFilesystem: true
```

Tambahkan `emptyDir` untuk `/tmp` dengan size limit. Jangan memakai memory-backed `/tmp` untuk PDF besar tanpa memasukkan ukuran ke memory budget pod.

Kubernetes mengirim signal langsung ke Odoo jika command memakai exec form. Wrapper shell yang tidak meneruskan signal harus dihindari.

## 14. Health Probes

Odoo 16 menyediakan:

```text
/web/health
/web/health?db_server_status=1
```

Pisahkan:

```text
liveness: proses HTTP hidup, tanpa DB dependency berat
readiness: registry/database siap menerima traffic
startup: beri waktu registry preload dan module initialization
```

Jangan memakai DB-checking endpoint sebagai liveness. Gangguan PostgreSQL tidak boleh menyebabkan Kubernetes me-restart semua Odoo pod sekaligus.

Probe interval tidak boleh menghasilkan connection/query pressure besar.

## 15. Static Assets dan Runtime Files

Static source tetap diperlukan untuk asset bundle compilation dan debug asset mode. Penghapusan source JS/SCSS/XML setelah prebuild memerlukan perubahan engine dan invalidation contract lebih besar.

Fase awal:

- pertahankan static source untuk addon terpilih;
- cache hashed `/web/assets/*` pada reverse proxy/CDN;
- jangan melayani static file besar melalui Python worker jika proxy dapat melayaninya;
- jangan memasukkan development source map atau test libraries yang tidak dipakai runtime.

## 16. Database Tooling

Odoo memanggil executable PostgreSQL untuk backup/restore:

```text
pg_dump
pg_restore
psql
```

Jika database manager dinonaktifkan dan backup dilakukan oleh operator PostgreSQL, `postgresql-client` dapat dihapus dari image setelah smoke test.

Trade-off:

```text
image lebih kecil
vs
Odoo database backup/restore feature tidak tersedia
```

Keputusan harus explicit. `list_db=False` sendiri belum membuktikan bahwa seluruh backup/restore path tidak dipakai.

## 17. Build Profiles

Jangan menghasilkan banyak image sebelum diperlukan. Satu release dapat memakai build arguments dengan manifest output.

Proposed profiles:

### `full`

```text
all runtime addons
all approved languages
wkhtmltopdf
selected fonts
PostgreSQL client
LDAP jika dipakai
```

### `production-lean`

```text
all required addon source
language allowlist
tests/docs/build metadata removed
wkhtmltopdf retained jika PDF aktif
PostgreSQL client optional
LDAP optional
```

### `closure-pruned`

```text
installed addon dependency closure only
language allowlist
feature-specific binaries only
```

Rekomendasi pertama: `production-lean`.

## 18. Image Benchmark Targets

Bandingkan current image dan candidate memakai architecture sama.

Target committed:

| Metrik | Target |
|---|---:|
| Docker build context | Turun minimal 70% |
| Unpacked image size | Turun minimal 40% |
| Compressed image size | Turun minimal 30% |
| Image pull-to-start | Turun minimal 25% |
| Cold startup-to-ready | Tidak memburuk; target turun 10–20% |
| Critical/high known CVE | 0 yang memiliki fix tersedia |
| Runtime compiler/dev headers | 0 |
| Process berjalan sebagai root | 0 |
| Functional/report/asset regression | 0 |

Stretch target setelah language dan addon closure pruning:

```text
unpacked image turun 60–75%
compressed image turun 45–65%
```

Steady-state target image-only:

```text
RAM: 0–5% improvement normal
CPU: 0–10% normal
```

Python version winner dapat memberi gain CPU lebih tinggi, tetapi hasil tersebut dicatat sebagai runtime-version optimization, bukan image-size optimization.

## 19. Validation Matrix

Setiap candidate image harus menjalankan:

```text
import semua installed addon
registry load
module install/update/uninstall
asset compile
LTR UI
RTL UI jika bahasa RTL aktif
login/session
cron
JSON-RPC
invoice PDF
sale PDF
barcode
image resize
email template rendering
Excel export/import
DB backup/restore jika feature dipertahankan
LDAP auth jika feature dipertahankan
gracious SIGTERM
read-only root filesystem test
```

Multi-architecture release menambah matrix per architecture.

## 20. Delivery Sequence

### Milestone 1: Inspect current production image

Butuh:

```text
current Dockerfile
entrypoint
.dockerignore
base image and digest
production architecture
final image compressed/unpacked size
docker history output
installed OS package list
installed pip package list
wkhtmltopdf version
active Odoo language list
installed Community/Enterprise/custom module list
```

### Milestone 2: Safe multi-stage image

Implementasi:

```text
Debian slim candidate
wheel builder
runtime-only libraries
non-root
clean build context
no translation/addon pruning yet
```

### Milestone 3: Production lean pruning

Implementasi:

```text
remove tests/docs/build metadata
language allowlist
optional PostgreSQL client/LDAP/RTL decisions
precompile bytecode A/B test
```

### Milestone 4: Runtime benchmark matrix

```text
Python 3.10 vs 3.11 vs 3.12
amd64/arm64 as required
full report regression
engine benchmark workload
```

### Milestone 5: Optional addon closure

Hanya jika image target belum tercapai dan deployment menerima immutable module catalog.

## 21. Recommended First Target

```text
Base: Debian slim, exact Python chosen by benchmark
Build: multi-stage wheelhouse
Runtime: no compiler/dev headers
Source: all required addons retained
Prune: .git, docs, packaging metadata, tests, unused translations
Reports: wkhtmltopdf retained until proven unused
DB tools: retain until backup/restore ownership confirmed
Security: fixed non-root UID, dropped capabilities, read-only root target
```

Expected primary gain:

```text
large image size reduction from translations and build artifacts
faster image pull and rollout
smaller attack surface
little direct steady-state RAM reduction
```

Engine plan remains responsible for large memory, CPU, and request-latency improvement.