# Arsitektur Produk Managed ERP

Status: baseline implementasi aktif pada branch `feat/react-client`.

Dokumen ini menjelaskan tujuan produk, alasan perubahan dari UI Odoo generik, batas tanggung jawab managed layer, keputusan domain, dan arah pengembangan. Detail katalog Product, Variant, Pricelist, dan UoM ada di [Managed Product Catalog](managed-product-catalog.md). Urutan kerja, pola implementasi, checkpoint, dan acceptance criteria untuk agent berikutnya ada di [Managed ERP Development Playbook and Handoff](managed-erp-development-playbook.md).

## 1. Tujuan produk

Managed ERP ditujukan sebagai ERP operasional Indonesia dengan:

- Odoo Community sebagai business engine;
- React sebagai UI utama yang lebih ringkas dan konsisten;
- managed addons sebagai product layer;
- data canonical tetap kompatibel dengan Sales, Purchase, Inventory, Accounting, dan localization Odoo;
- dukungan bisnis Indonesia tanpa mematikan kebutuhan foreign customer/vendor, multi-currency, fiscal position, Incoterm, language, dan dokumen internasional.

North star:

> User bekerja dengan istilah dan alur bisnis, sementara Odoo tetap menjaga aturan transaksi, compute, onchange, ACL, record rules, stok, accounting, pajak, procurement, pricing, dan audit trail.

Produk ini bukan skin yang menampilkan seluruh model Odoo. Produk ini memilih workflow yang aman, memberi kontrak field yang jelas, dan menyembunyikan detail teknis yang tidak dibutuhkan user harian.

## 2. Masalah yang diselesaikan

UI Odoo generik kuat, tetapi langsung mengekspos struktur implementasi:

- satu `res.partner` dipakai untuk customer, vendor, PIC, alamat, dan contact;
- Product Template dan Product Variant mudah disalahartikan sebagai dua produk berbeda;
- UoM menampilkan `factor`, `reference`, `bigger`, dan `smaller` alih-alih kalimat konversi bisnis;
- Pricelist adalah rule engine fleksibel, tetapi form teknis sulit dipakai untuk harga channel atau variant;
- form besar mencampur data umum, advanced settings, computed fields, dan konfigurasi operator;
- generic CRUD dapat melewati intent workflow walau model dan ACL masih valid.

Perubahan managed dibuat untuk mengurangi kesalahan tersebut tanpa mengganti engine Odoo.

## 3. Batas arsitektur

Source ownership:

```text
src/odoo    = framework Odoo
src/addons  = retained native Community addons
managed     = managed product addons
```

Nama teknis addon managed mengikuti folder langsung, misalnya `core`, `directory`, `products`, dan `sales`. Karena XML ID berubah, database lama tidak dimigrasikan untuk refactor ini; development database dibuat ulang.

### 3.1 Odoo tetap memiliki business engine

Managed layer tidak menulis ulang:

- accounting entries dan reconciliation;
- stock move, reservation, on-hand, forecast, lot/serial;
- sales dan purchase compute/onchange;
- tax, fiscal position, currency, dan localization;
- product attribute combination;
- Product Variant generation;
- Pricelist calculation;
- UoM quantity/price conversion;
- ACL, record rules, company isolation, dan audit fields.

Method native yang tetap menjadi sumber kebenaran antara lain:

```text
product.template / product.product
product.attribute / product.attribute.value
product.pricelist / product.pricelist.item
uom.uom._compute_quantity()
uom.uom._compute_price()
res.partner.address_get()
```

### 3.2 Managed addons menjadi product layer

Managed layer bertanggung jawab atas:

- curated navigation;
- action-specific read/write contract;
- istilah dan layout bisnis;
- validation tambahan pada managed context;
- normalization dan duplicate guard;
- defaults dan managed module activation;
- relation editor yang aman;
- workflow guidance;
- archive policy;
- API serialization dan transaction boundary.

Managed layer tidak boleh membuat model pengganti jika model native sudah cukup.

### 3.3 React menjadi presentation layer

React menangani:

- custom forms untuk workflow kompleks;
- metadata-driven forms untuk CRUD sederhana;
- conditional disclosure;
- relation draft editor;
- image upload dan preview;
- business labels dan help text;
- responsive layout.

XML view tetap tersedia sebagai migration fallback, bukan contract utama setelah domain dimigrasi.

## 4. Contract managed UI

Alur contract:

```text
Menu
→ ir.actions.act_window dengan XML ID stabil
→ model._managed_ui_contract(action_xmlid)
→ /api/v1/ui/actions/<action_id>
→ schema read/write/action allowlist
→ React custom renderer atau metadata renderer
```

Action XML ID menjadi anchor. Model yang sama dapat memiliki form berbeda untuk intent berbeda.

Contoh:

```text
customers.action_customers
vendors.action_vendors
contact_persons.action_contacts
products.action_products
products.action_product_attributes
products.action_product_categories
products.action_product_pricelists
products.action_uom_categories
```

Prinsip keamanan:

1. Tombol tersembunyi bukan security boundary.
2. Endpoint memeriksa action visibility, ACL, record rules, dan contract permission.
3. Hanya field dalam write allowlist yang dikirim ke ORM.
4. Relation domain ditetapkan server-side untuk target sensitif.
5. Create, update, dan delete managed dibungkus database savepoint agar nested failure tidak meninggalkan perubahan parsial.

## 5. Keputusan domain dan alasan perubahan

| Area | Keputusan | Alasan |
|---|---|---|
| Customer dan Vendor | Tetap satu canonical `res.partner`, role dipisah | Satu badan hukum dapat membeli dan menjual; duplicate identity merusak accounting dan histori |
| PIC | Action/form terpisah, data tetap child `res.partner` | User perlu workflow PIC, tetapi integrasi native membutuhkan partner hierarchy |
| Employee | Tetap domain HR | Private identity, bank, dan data personal harus mengikuti ACL HR |
| Address | Facade `managed.partner.address`, fisik tetap child `res.partner` | UX perlu label/default/archive; Sales dan Invoice tetap memakai `address_get()` native |
| Wilayah Indonesia | Dataset lokal canonical dan cascading selector | Penulisan alamat bebas menghasilkan variasi kota/kecamatan/kode pos dan sulit dipakai dokumen pajak/pengiriman |
| Product | Master utama tetap `product.template` | Identitas bersama, default harga, category, tax, dan policy berada pada template native |
| Variant | SKU transaksi tetap `product.product` | Sales, stock, barcode, dan channel harus menunjuk kombinasi fisik yang spesifik |
| Attribute | Master terpisah; Product hanya memilih existing Attribute/Value | Mencegah duplikasi `Warna`, `Ukuran`, atau `Isi kemasan` per Product |
| Category | Tetap hierarchy `product.category` | Accounting defaults dan reporting native bergantung pada category canonical |
| Pricelist | Tetap native rule engine | Harga per customer, channel, currency, quantity, periode, product, dan variant sudah ditangani Odoo |
| UoM | UI berpusat pada `uom.category` | Invariant utamanya satu kelompok, satu satuan dasar, dan banyak satuan konversi |
| Packaging | Gunakan `product.packaging`, bukan UoM global | Rasio dus/pack berbeda per Product dan tidak boleh mengubah makna quantity global |
| Stock | Read-only dari stock engine | Menulis On Hand dari Product form akan melewati stock move dan valuation |
| Delete master | Archive atau pindahkan referensi | Histori transaksi harus tetap dapat membaca Product, Pricelist, UoM, Address, dan relation lama |

## 6. Identity dan directory

### 6.1 Canonical identity

```text
res.partner
├── managed.partner.role: customer
├── managed.partner.role: vendor
└── managed.partner.role: contact
```

Satu partner dapat memiliki lebih dari satu role pada company yang sama. Constraint:

```text
unique(partner_id, company_id, role)
```

Customer dan Vendor bukan tabel identity baru.

### 6.2 Duplicate policy

Current enforcement:

- normalized NPWP/TIN exact: block;
- normalized NIK exact: block;
- company scope dihormati;
- nama sama tidak otomatis diblokir.

Target hardening yang belum selesai:

- search-first create;
- pilih existing identity lalu tambah role;
- warning email/phone;
- fuzzy-name candidate;
- merge/review flow untuk legacy duplicate.

Email, phone, atau nama tidak boleh menjadi hard block tanpa review karena dapat dipakai bersama atau berubah.

### 6.3 Address

Facade:

```text
managed.partner.address
└── address_partner_id → child res.partner
```

Mapping native:

```text
billing  → type=invoice
shipping → type=delivery
other    → type=other
```

Aturan:

- default billing dan default shipping terpisah;
- maksimal satu default aktif per account dan purpose;
- alamat historis diarsipkan, bukan dihapus;
- `res.partner.address_get()` memilih managed default;
- foreign address tetap menerima free-form city/state/postal code;
- alamat Indonesia memakai Province → Regency/City → District → Village → Postal Code.

## 7. Product catalog

Navigation aktif:

```text
Products
├── Products
├── Atribut
├── Kategori
├── Daftar Harga
└── Satuan
```

Semua menu memakai model native dengan managed action/form. Detail keputusan dan contoh ada di [Managed Product Catalog](managed-product-catalog.md).

Ringkasan batas konsep:

```text
Product Template = identitas keluarga produk
Product Variant  = SKU/kombinasi yang benar-benar ditransaksikan
Attribute        = dimensi pilihan pembentuk variant
Category         = klasifikasi/reporting/account defaults
Pricelist        = aturan harga berdasarkan konteks
UoM              = konversi quantity dalam dimensi yang sama
Packaging        = isi kemasan per Product
```

## 8. Draft relation editor

Relation kompleks seperti Address, PIC, Bank, Vendor Price, Variant, Attribute Line, Pricelist Rule, dan UoM Unit diedit sebagai draft lokal.

```text
Buka drawer
→ ubah local draft
→ Batal: buang draft
→ Simpan: commit ke draft parent
→ Simpan parent: kirim nested commands ke ORM
```

Alasan:

- tombol `Batal` harus benar-benar tidak mengubah parent;
- user dapat menyelesaikan satu relation sebelum menyimpan dokumen;
- nested onchange tetap bisa dipanggil tanpa premature write;
- validation parent dan child tetap atomic pada save.

## 9. Aktivasi managed module dan permission

Managed addon yang terpasang langsung menampilkan seluruh workflow miliknya. Tidak ada feature flag per sub-feature.

Contoh:

```text
products terpasang → Product, Atribut, Kategori, Daftar Harga, Satuan, dan Variant aktif
customers terpasang → Customer aktif
vendors terpasang → Vendor aktif
contact_persons terpasang → Contact Person/PIC aktif
people terpasang → Employee directory aktif untuk user yang lolos ACL HR
```

Visibility bukan pengganti security. ACL, record rules, company scope, dan write allowlist tetap menentukan siapa yang boleh membaca atau mengubah data. Feature flag per managed module dapat dirancang nanti jika ada kebutuhan produk konkret; belum diimplementasikan sekarang.

## 10. Tenant Settings dan role

Managed ERP memakai invariant operasional:

```text
1 tenant = 1 database = 1 legal company = 1 data boundary
```

Company tambahan diprovision sebagai tenant baru; Managed Settings tidak menyediakan create, switch, atau assignment multi-company. Billing ditunda.

Addon `settings` menyediakan General Information, Pengguna, Role & Akses, serta setting kontribusi dari managed addon aktif. `managed.settings.registry` mengumpulkan section, provider, readiness, action/menu permission, dan permission catalog. Products dan Sales sudah menjadi contribution pertama. Permission memakai level `None`, `Read`, atau `Write`; user mendapat role tenant-wide dan effective permission mengambil level tertinggi. Tidak ada direct per-user override, deny override, raw ACL editor, sub-feature flag, atau custom audit. Native Odoo ACL, record rules, metadata audit, dan chatter tetap boundary akhir.

UX managed wajib seamless dan clean:

- gunakan satu judul utama; jangan ulangi label konteks pada badge, eyebrow, card, dan section;
- hapus subtitle yang hanya mengulang judul atau menjelaskan hal yang sudah terlihat;
- list dan form mengisi lebar area konten, tidak menggantung di tengah tanpa alasan;
- hindari card, rounded container, border, dan shadow bertingkat; gunakan hierarchy, whitespace, dan separator tipis;
- label field harus singkat, konsisten, bebas typo, dan memakai istilah bisnis;
- status atau helper text hanya tampil jika membantu keputusan atau mencegah kesalahan;
- satu aksi utama per konteks; hindari tombol atau navigasi duplikat.

## 11. Navigation policy

Navigation disusun berdasarkan task bisnis, bukan daftar model. Managed app hanya mengirim menu yang action-nya menjadi anchor managed terdaftar; parent native dapat tampil hanya untuk mengelompokkan child managed. Menu native lain tidak tampil sebelum workflow managed-nya tersedia. Allowlist ini juga berlaku pada endpoint action managed; action native yang tidak terdaftar ditolak server-side.

Contoh Contacts:

```text
Contacts
├── Customers
├── Vendors
└── Contact Persons
```

Tidak ada menu generic Partner CRUD. Alasan: generic Partner tidak menjelaskan role, tax profile, payment defaults, address purpose, atau PIC relationship.

Contoh Product:

```text
Products
├── Products
├── Atribut
├── Kategori
├── Daftar Harga
└── Satuan
```

Tidak ada menu factor UoM, raw attribute line, Product Variant CRUD terpisah, atau Pricelist Item CRUD terpisah.

Sales memakai ownership berbasis task:

```text
Penjualan
├── Penawaran
└── Pesanan

Persediaan
└── Pengiriman

Keuangan
├── Faktur Pelanggan
└── Pembayaran
```

Customer tetap dikelola di Contacts, Product/Variant serta Daftar Harga tetap di Products, pengiriman operasional dimiliki Persediaan, invoice dan pembayaran dimiliki Keuangan, pengaturan penjualan berada di Pengaturan, dan analitik akan menjadi workspace lintas domain terpisah. Pesanan menjadi control tower kecil: menampilkan status native, membuka Pengiriman/Faktur managed, dan membuat draft faktur melalui wizard native; tidak membuat CRUD Stock atau Accounting kedua di Sales.

## 12. Status implementasi

| Domain | Status | Catatan |
|---|---|---|
| Managed UI contract | Selesai baseline | Action anchor, read/write allowlist, custom renderer, XML fallback |
| Inbox | Selesai baseline | Channel, pesan langsung, mention, aktivitas, unread, composer; native Mail tetap engine |
| Customer | Selesai baseline | Profile, address, PIC, sales/finance, tax |
| Vendor | Selesai baseline | Purchase/finance, tax, bank, supplier price |
| Contact Person | Selesai baseline | Context “Terhubung ke” dan role contact |
| Employee directory | Selesai baseline | Data private tetap HR ACL |
| Indonesia regions | Selesai | 38 province, 514 regency/city, 7.285 district, 83.762 village |
| Product | Selesai baseline | Identity, type, stock status, sales, purchase, tax/accounting |
| Attribute/Variant | Selesai baseline | Native combinations, per-variant identity/cost/stock, `price_extra` |
| Category | Selesai baseline | Native hierarchy, duplicate sibling guard, no managed delete |
| Pricelist | Selesai baseline | Global/category/product/variant rules, fixed/discount/formula |
| UoM | Selesai baseline | Category-centered editor, `ml`, conversion facade, transaction lock |
| Sales quotation | Baseline aktif | Managed Penawaran/Pesanan, Customer selector, Variant line editor, native onchange/pricing, confirmation |
| Sales fulfillment | Baseline aktif | Pesanan merangkum dan deep-link ke custom managed Pengiriman/Faktur/Pembayaran; native Delivery, invoice wizard, posting, dan payment tetap engine |
| Marketplace connector | Belum ada | Store mapping, price sync, order import, settlement perlu domain terpisah |
| Contact duplicate candidate flow | Belum lengkap | Exact legal identity block sudah ada |
| Full browser visual QA | Belum lengkap | Perlu desktop/mobile dan role matrix |

## 13. Roadmap

Urutan produk:

1. Stabilkan Product catalog dan browser QA.
2. Selesaikan Sales end-to-end dengan pemilihan `product.product`.
3. Selesaikan search-first identity dan duplicate candidate flow.
4. Tambahkan Purchase dan Stock operational workflow.
5. Tambahkan Invoice, Payment, dan Coretax preflight.
6. Jika omnichannel dimulai, buat connector/store mapping ke Pricelist dan Product Variant canonical.
7. Catat marketplace fee dan settlement di Accounting; jangan mengurangi harga katalog.

## 14. Release gate

Perubahan managed domain wajib memeriksa:

- canonical model tetap native jika tersedia;
- action XML ID stabil;
- schema source `managed`;
- read/write field allowlist;
- endpoint permission, bukan hanya hidden button;
- relation domain server-side;
- nested onchange bila model native memerlukannya;
- failed nested write rollback penuh;
- archive/history policy;
- ACL dan company scope;
- desktop/mobile form layout;
- runtime API dan database integration.

Minimum checks saat ini:

```bash
python3 -m py_compile <changed-python-files>
python3 scripts/test_managed_addon_scope.py
cd frontend && npm run check
cd frontend && npm run build
git diff --check
curl http://127.0.0.1:8069/web/health
```

Full Odoo test suite tetap release gate. Local runner saat ini masih dapat terhambat dependency `odoo.addons.website` dan port conflict; runtime API checks bukan pengganti test suite tersebut.

## 15. Implementation map

Fulfillment dan finance:

```text
managed/inventory/models/stock_picking.py
managed/inventory/views/actions.xml
managed/inventory/frontend/delivery-form.tsx
managed/finance/models/account_move.py
managed/finance/views/actions.xml
managed/finance/frontend/invoice-form.tsx
managed/finance/frontend/payment-form.tsx
managed/sales/models/sale_order.py
managed/sales/frontend/sale-order-form.tsx
```

Core contract dan API:

```text
managed/core/models/base.py
managed/core/controllers/ui_api.py
frontend/src/views/view-metadata.ts
frontend/src/views/view-registry.ts
frontend/src/views/field-registry.tsx
```

Directory:

```text
managed/directory/models/directory.py
managed/directory/frontend/party-form.tsx
managed/indonesia_regions/models/region.py
managed/indonesia_regions/data/regions.csv
```

Product catalog:

```text
managed/products/models/product.py
managed/products/models/uom.py
managed/products/frontend/product-form.tsx
managed/products/frontend/variant-manager.tsx
managed/products/frontend/attribute-form.tsx
managed/products/frontend/category-form.tsx
managed/products/frontend/pricelist-form.tsx
managed/products/frontend/pricelist-rules.tsx
managed/products/frontend/uom-form.tsx
managed/products/frontend/uom-units.tsx
managed/products/views/actions.xml
```

## 16. Traceability commit

Baseline yang dibahas dokumen ini dibangun lewat commit berikut:

```text
e2d297e3 Build managed product catalog
7e11b92e Complete managed product variants
7000c34b Add managed product attributes
eaba09fa Simplify managed attribute workflow
47f3a6ca Manage product categories and pricelists
def73bbd Add managed units of measure
fe9f7e67 Fix variant pricelist selection
```

Commit membantu audit perubahan, tetapi contract dan dokumen pada branch aktif tetap menjadi rujukan status terbaru.

## 17. Inbox dan komunikasi

`managed/discuss` menjadi product layer atas native Odoo Mail:

```text
Inbox      = perhatian user
Channel    = komunikasi tim
Aktivitas  = pekerjaan terjadwal
Chatter    = konteks record bisnis
```

Canonical data tetap `mail.channel`, `mail.channel.member`, `mail.message`, `mail.activity`, `mail.followers`, dan `ir.attachment`. Managed layer hanya memberi curated API, unread aggregation, deep link, composer, permission, dan React UX. Channel membership serta akses record tetap security boundary. Fresh tenant membuat satu channel `Umum`; tidak ada channel otomatis per customer atau transaksi. Internal note dan outbound customer message wajib tetap dipisah saat contextual chatter ditambahkan.

Inbox memakai dua panel: list kontekstual di kiri dan thread aktif di kanan. Tab `Pesan`, `Mention`, dan `Aktivitas` mengganti isi panel kiri. Pesan baru memakai drawer; pembuatan channel mendukung anggota private atau seluruh pengguna internal. Badge sidebar menunjukkan pesan belum dibaca; bell menunjukkan mention serta aktivitas terlambat atau jatuh tempo hari ini. Thread memakai bubble, pengelompokan pengirim, pemisah tanggal, dan divider unread.

Composer Inbox mendukung emoji, lampiran native `ir.attachment`, reply melalui `mail.message.parent_id`, reaction native, optimistic sending/retry, receipt direct chat berbasis `fetched_message_id`/`seen_message_id`, typing indicator native bus, presence native `im_status`, dan sound opt-out per browser. Lampiran dibatasi 10 file per pesan dan 25 MB per file; executable diblokir. Managed layer tidak membuat model chat baru.

Endpoint managed Inbox:

```text
GET  /api/v1/inbox
GET  /api/v1/inbox/counts
GET  /api/v1/inbox/channels/<id>
POST /api/v1/inbox/channels/<id>/messages
POST /api/v1/inbox/channels/<id>/attachments
POST /api/v1/inbox/channels/<id>/attachments/delete
POST /api/v1/inbox/channels/<id>/seen
POST /api/v1/inbox/channels/<id>/typing
POST /api/v1/inbox/channels/<id>/messages/<message_id>/reaction
POST /api/v1/inbox/direct
POST /api/v1/inbox/channels
POST /api/v1/inbox/activities/<id>/done
```

Tidak ada model pesan, channel, notifikasi, atau aktivitas pengganti di managed layer.
