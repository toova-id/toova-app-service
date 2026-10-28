# Managed ERP Development Playbook and Handoff

Status: active continuation guide for branch `feat/react-client`.

Dokumen ini menjelaskan cara agent/developer melanjutkan pekerjaan tanpa merusak keputusan domain yang sudah dibuat. Product goal dan boundary ada di [Managed ERP Product Architecture](managed-erp-product-architecture.md). Product catalog contract ada di [Managed Product Catalog](managed-product-catalog.md). Dokumen ini fokus pada pola kerja, current checkpoint, dan next execution plan.

## 1. Mulai setiap sesi

Baca berurutan:

1. [Managed ERP Product Architecture](managed-erp-product-architecture.md).
2. [Managed Product Catalog](managed-product-catalog.md) jika menyentuh Product, Variant, Pricelist, UoM, atau Packaging.
3. File model native Odoo untuk domain yang dikerjakan.
4. Managed contract, frontend, tests, dan self-check domain terkait.
5. Git state dan commit terbaru.

Commands:

```bash
git status --short
git log -10 --oneline
python3 scripts/test_managed_addon_scope.py
```

Runtime development saat checkpoint ini:

```text
App container: erp-local-app
DB container: erp-local-db
Database: erp_local
URL: http://127.0.0.1:8069
```

Ambil development login dari konfigurasi local environment. Jangan simpan password, database secret, token, atau production credential dalam dokumentasi.

## 2. Decision ladder

Sebelum menulis model atau engine baru, jawab berurutan:

```text
1. Apakah fitur ini benar-benar perlu ada?
2. Apakah model/method native Odoo sudah menangani domainnya?
3. Apakah managed layer cukup memberi contract, label, domain, validation, atau workflow?
4. Apakah komponen/field editor yang sudah ada dapat dipakai?
5. Apa diff minimum yang menjaga invariant?
```

Default decision:

```text
Native Odoo model + managed contract + focused React workflow
```

Hindari:

- model pengganti untuk model native;
- compute/accounting/stock/pricing engine baru;
- direct SQL untuk business write;
- Product duplikat per channel;
- generic CRUD untuk workflow stock/accounting kompleks;
- abstraction untuk satu use case;
- config “untuk nanti” tanpa requirement aktif.

## 3. Pattern implementasi managed domain

### 3.1 Action sebagai anchor

Setiap domain managed harus punya XML ID stabil:

```text
managed_<domain>.action_<intent>
```

Contoh:

```text
managed_products.action_product_pricelists
```

Action menentukan intent, visibility, model, dan contract. Jangan mendeteksi form hanya dari model karena satu model dapat memiliki beberapa intent.

### 3.2 Contract backend

Implementasikan:

```python
@api.model
def _managed_ui_contract(self, action_xmlid):
    if action_xmlid != 'module.action_xmlid':
        return super()._managed_ui_contract(action_xmlid)
    return {
        'list': {...},
        'form': {
            'fields': [...],
            'write_fields': [...],
            'buttons': [...],
        },
    }
```

Contract wajib membatasi:

- list fields;
- form read fields;
- write fields;
- create/write/delete capability;
- buttons;
- nested relation columns.

Menampilkan field tidak otomatis berarti field boleh ditulis.

### 3.3 Managed validation

Validation product-layer hanya aktif pada managed context jika tidak dimaksudkan mengubah seluruh perilaku Odoo:

```python
if self.env.context.get('managed_ui'):
    ...
```

Gunakan native constraint tanpa context gate bila invariant memang universal dan aman untuk semua integration paths.

Managed validation umum:

- trim required names;
- normalized duplicate detection;
- company scope;
- case-insensitive comparison;
- archive instead of delete;
- immutable ratio/reference after transaction use.

Error harus menggunakan istilah bisnis, bukan nama field teknis.

### 3.4 Relation editor

Gunakan local draft:

```text
Open drawer
→ copy row ke draft
→ edit draft
→ Batal membuang draft
→ Simpan mengubah draft parent
→ save parent mengirim nested commands
```

Jangan write child saat drawer baru ditutup. Atomic commit terjadi saat parent disimpan.

Nested relation yang butuh native onchange memakai:

```text
POST /api/v1/ui/actions/<action_id>/relations/<field_name>/onchange
```

### 3.5 Relation domain

Filter relation penting harus ditegakkan server-side di `addons/web/controllers/ui_api.py`, bukan hanya frontend.

Contoh:

```text
Pricelist Variant → product.product milik Product terpilih
Purchase UoM      → uom.uom dalam Category stock UoM
Attribute Value   → value milik Attribute terpilih
Vendor Variant    → variant milik Product terpilih
Category Parent   → bukan diri sendiri atau subtree
```

Jika parent belum dipilih, selector child sensitif harus kosong:

```python
[('id', '=', 0)]
```

### 3.6 Native onchange dan user intent

Native onchange tetap dipakai, tetapi jangan biarkan hasilnya menghapus intent UI yang user pilih secara eksplisit.

Contoh bug yang sudah diperbaiki:

```text
User memilih Pricelist scope “Variant tertentu”
→ native onchange melihat Product kosong
→ native onchange mengubah scope ke global
→ field Variant hilang
```

Pattern fix:

```text
Preserve explicit scope
Apply native onchange values lain
Re-apply explicit scope pada merged draft
```

Setiap conditional form harus dites sebagai sequence interaksi, bukan hanya schema existence.

### 3.7 API atomicity

Managed create, update, dan delete harus tetap berada dalam database savepoint:

```python
with request.env.cr.savepoint():
    record.write(values)
```

Alasan: nested child mutation dapat terjadi sebelum final constraint gagal. Tanpa savepoint, response error dapat meninggalkan perubahan parsial.

Jangan menghapus savepoint saat refactor controller.

### 3.8 Custom form vs metadata form

Gunakan metadata form bila:

- CRUD sederhana;
- sedikit conditional fields;
- tidak ada multi-step workflow;
- nested relation sederhana.

Gunakan custom React form bila:

- form punya business tabs;
- relation editor kompleks;
- banyak conditional states;
- summary/computed metrics perlu hierarchy khusus;
- workflow tidak aman sebagai generic CRUD.

Custom form tetap menerima schema contract. Jangan hard-code permission terpisah dari schema.

## 4. Domain pattern yang sudah ditetapkan

### Directory

```text
Identity canonical → res.partner
Role               → managed.partner.role
Address facade     → managed.partner.address
Physical address   → child res.partner
```

Customer, Vendor, dan PIC adalah workflow berbeda atas identity canonical, bukan identity table terpisah.

### Product

```text
Master/family → product.template
SKU/Variant   → product.product
Stock         → computed native
Vendor price  → product.supplierinfo
```

### Attribute dan Variant

```text
Attribute master dibuat terpisah
Product memilih existing Attribute/Value
Odoo membuat native combinations
Sales memilih product.product
```

### Pricing

```text
Harga dasar Product       → product.template.list_price
Tambahan normal Variant   → product.template.attribute.value.price_extra
Harga contextual/channel  → product.pricelist.item
Harga aktual transaksi    → Sales Order Line snapshot
Marketplace fee           → settlement/accounting
```

### UoM dan Packaging

```text
Quantity conversion global → uom.category + uom.uom
Variant kemasan             → Attribute/Variant
Kemasan logistik per Product → product.packaging
```

## 5. Current checkpoint

Current Product navigation:

```text
Products      managed
Atribut       managed
Kategori      managed
Daftar Harga  managed
Satuan        managed
```

Latest functional commits at this checkpoint:

```text
fe9f7e67 Fix variant pricelist selection
def73bbd Add managed units of measure
47f3a6ca Manage product categories and pricelists
7e11b92e Complete managed product variants
e2d297e3 Build managed product catalog
```

Architecture documentation baseline:

```text
98257919 Document managed ERP product architecture
```

Implemented catalog baseline:

- Product custom form;
- Attribute master and values;
- native Variant generation;
- per-Variant SKU, barcode, image, cost, weight, volume, stock display;
- `price_extra` editor;
- Category hierarchy;
- Pricelist global/category/Product/Variant rules;
- fixed, percentage, and formula pricing;
- UoM category-centered editor;
- canonical `ml`;
- UoM transaction lock;
- atomic nested managed API writes.

Known runtime facts:

```text
Luma Test Product template ID: 1
Active variants during latest validation:
- product.product 19: XL
- product.product 20: L
```

IDs are local fixtures, not stable contract. Never hard-code them.

## 6. Next execution plan

### Phase A — catalog closeout

Goal: declare catalog safe enough for Sales integration.

Tasks:

1. Browser QA Product, Attribute, Category, Pricelist, and UoM.
2. Test desktop and mobile widths.
3. Test permission matrix: normal user, Product manager, Accounting user, admin.
4. Test create/edit/archive and failed validation rollback.
5. Verify Product Variant selection in Pricelist through browser, not API only.
6. Normalize remaining Product labels to Bahasa Indonesia.
7. Decide whether managed Product Packaging editor is needed before Sales; do not build it without concrete order-entry requirement.

Acceptance:

```text
No XML fallback on managed catalog actions
No selector leaks unrelated records
No failed nested write leaves child data
All stock metrics remain read-only
Variant-specific Pricelist works in browser
Responsive form has no horizontal overflow
```

### Phase B — Sales end-to-end

Goal:

```text
Quotation → Confirmation → Delivery → Invoice → Payment status
```

Required design rules:

- Sales line chooses `product.product`;
- customer Pricelist supplies default price;
- variant-specific rule works;
- line price remains transaction snapshot after save;
- Product onchange fills description, UoM, tax, and price;
- user edits quantity/UoM only within native constraints;
- confirmation uses native action/method;
- delivery uses Stock workflow, not direct state write;
- invoice uses native invoice creation;
- payment status remains computed Accounting state.

First implementation slice:

```text
Create quotation
→ select Customer
→ select Pricelist
→ add Variant line
→ run nested onchange
→ save draft
→ reopen and verify snapshot
```

Do not start Delivery/Invoice UI before quotation line behavior and permission tests pass.

Acceptance for first slice:

- selecting Product Variant populates description, UoM, tax, and price;
- changing quantity selects correct minimum-quantity Pricelist rule;
- changing Pricelist recalculates draft lines through native onchange;
- Variant L and XL can receive different prices;
- foreign currency works through native Pricelist currency;
- save/reopen preserves price and selected Variant;
- unauthorized fields are not accepted by API.

### Phase C — directory hardening

Goal: prevent duplicate business identities during operational use.

Tasks:

- search-first create;
- select existing identity and add Customer/Vendor role;
- email/phone duplicate warning;
- fuzzy-name candidates;
- legacy address backfill;
- PIC parent filtering;
- browser QA all address/PIC drawers.

Legal identity exact remains hard block. Email, phone, and fuzzy name remain candidate/warning flow.

### Phase D — test infrastructure

Fix blockers:

```text
ModuleNotFoundError: No module named 'odoo.addons.website'
OSError: [Errno 98] Address already in use
```

Full Odoo test suite is required before production release. Runtime API tests and self-check scripts are useful but not equivalent.

## 7. Omnichannel future boundary

Do not create connector models during Sales work unless omnichannel connector is explicitly in scope.

When started, required design artifact before code:

```text
Store/channel identity
Company and warehouse mapping
Pricelist mapping
External template/variant mapping
Price publish lifecycle
Order import idempotency
Stock sync policy
Cancellation/return policy
Fee and settlement accounting
```

Expected mapping:

```text
Store                 → product.pricelist
External item ID      → product.template
External model/SKU ID → product.product
Imported order price  → sale.order.line snapshot
Platform fee          → accounting settlement line
```

Pricelist is ready as pricing foundation. Connector, publishing, order import, and settlement are not implemented.

## 8. Required checks per change

### Python/backend change

```bash
python3 -m py_compile <changed-files>
python3 scripts/test_managed_addon_scope.py
git diff --check
```

### Frontend change

```bash
cd frontend
npm run check
npm run build
```

### Runtime change

```bash
curl http://127.0.0.1:8069/web/health
```

Then verify:

- action schema source is `managed`;
- action visible only for intended groups;
- create/update/delete permission matches contract;
- relation selectors enforce server domain;
- nested failure fully rolls back;
- database stores canonical native model fields.

### Non-trivial interaction

Leave one runnable self-check or focused test. Schema string checks alone do not prove interaction correctness; add runtime/API or browser sequence when state transitions matter.

## 9. Documentation rule

Update documentation in same commit when changing:

- domain ownership;
- canonical model;
- user-visible workflow;
- validation/invariant;
- permission/capability;
- roadmap status;
- operational boundary.

Use:

```text
managed-erp-product-architecture.md
```

for cross-domain product decisions.

Use:

```text
managed-product-catalog.md
```

for Product catalog contract.

Use this file for:

- implementation pattern;
- current checkpoint;
- next execution plan;
- known blockers;
- acceptance criteria.

Do not put secrets, local database secret, production credentials, or personal tokens in docs.

## 10. Stop conditions

Stop and request a decision before code if:

- requirement creates a new canonical model alongside an existing Odoo model;
- Product, Variant, UoM, Packaging, and Pricelist concepts are being mixed;
- accounting posting behavior changes;
- stock quantity would be directly written;
- marketplace gross price, fee, and settlement are conflated;
- deletion could invalidate transaction history;
- multi-company ownership is unclear;
- proposed workflow bypasses native confirmation/posting methods;
- requirement changes legal/tax treatment without domain review.

## 11. Definition of done

A managed feature is done only when:

```text
Domain decision documented
Canonical native model identified
Action XML ID stable
Managed contract explicit
Write allowlist minimal
ACL and record rules preserved
Server-side relation domain present
Validation errors business-readable
Nested changes atomic
Frontend follows draft/save/cancel semantics
Runtime behavior verified
Self-check/test added
Docs and status updated
Working tree clean
```
