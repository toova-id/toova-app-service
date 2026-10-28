# Managed Product Catalog

Status: implementasi baseline aktif.

Dokumen ini menjadi contract domain dan UX untuk Product, Attribute, Variant, Category, Pricelist, UoM, dan Packaging. Tujuan utamanya mencegah model yang benar dipakai untuk konsep yang salah. Cara melanjutkan implementasi dan acceptance criteria task berikutnya ada di [Managed ERP Development Playbook and Handoff](managed-erp-development-playbook.md).

## 1. Goal

Managed Product Catalog harus memastikan:

- satu barang/jasa memiliki identity canonical;
- SKU dan barcode menunjuk variant yang benar;
- stock tetap dihitung native;
- harga dasar, tambahan harga variant, dan harga contextual tidak tercampur;
- quantity dan konversi konsisten pada Sales, Purchase, Stock, dan Invoice;
- user dapat mengelola master data tanpa memahami field teknis Odoo;
- catalog siap menjadi sumber Product/Variant bagi Sales dan connector channel.

Bukan goal:

- menulis ulang Product, Variant, Pricelist, atau UoM engine;
- menyimpan On Hand dari Product form;
- membuat Product terpisah untuk setiap channel;
- memakai UoM untuk label kemasan;
- memakai Pricelist untuk marketplace fee atau settlement.

## 2. Canonical model map

| Konsep bisnis | Model canonical | Catatan |
|---|---|---|
| Product family/master | `product.template` | Nama, type, category, default sales/cost/tax/policy |
| SKU/variant | `product.product` | Combination, SKU, barcode, image, cost, weight, volume, stock |
| Attribute master | `product.attribute` | Warna, Ukuran, Isi kemasan |
| Attribute value | `product.attribute.value` | Merah, XL, 250 ml |
| Attribute pada Product | `product.template.attribute.line` | Attribute dan values yang dipakai Product |
| Value pada Product | `product.template.attribute.value` | Menyimpan `price_extra` |
| Vendor price | `product.supplierinfo` | Vendor, variant scope, minimum, price, currency, lead time |
| Category | `product.category` | Hierarchy, report, account defaults |
| Pricelist | `product.pricelist` | Identitas daftar harga/currency/company |
| Pricelist rule | `product.pricelist.item` | Scope, method, quantity, period |
| UoM group | `uom.category` | Dimensi quantity, misalnya Volume atau Weight |
| UoM | `uom.uom` | L, ml, kg, g dan conversion ratio |
| Product packaging | `product.packaging` | Rasio kemasan khusus Product, misalnya satu dus berisi 12 unit |

## 3. Product Template dan Product Variant

### 3.1 Identity

```text
product.template
└── product.product
```

Jika tidak ada Attribute pembentuk variant, Product tetap memiliki satu `product.product` internal. Jika Attribute aktif, setiap kombinasi menjadi `product.product`.

Contoh:

```text
Template: Kaos Luma
Attribute: Ukuran
Values: L, XL

Variants:
- Kaos Luma (L)
- Kaos Luma (XL)
```

Sales, Stock, barcode scan, dan channel order harus memilih `product.product`, bukan hanya template.

### 3.2 Managed Product type

UI menyederhanakan native `detailed_type`:

```text
Goods + Track Inventory aktif → product
Goods + Track Inventory mati  → consu
Service                       → service
```

Alasan:

- user memilih intent bisnis;
- Odoo tetap menerima nilai native yang dipakai Stock dan Accounting;
- tidak ada type engine baru.

### 3.3 Stock

`On Hand` dan `Forecast` read-only:

```text
On Hand  = hasil stock engine
Forecast = on hand + incoming − outgoing
```

Stock tidak pernah diedit dari Product master. Perubahan quantity harus melalui Receipt, Delivery, Inventory Adjustment, Manufacturing, Return, atau workflow stock native lain.

Service menampilkan empty state karena tidak memiliki persediaan.

### 3.4 SKU dan barcode

SKU canonical berada pada `product.product.default_code`.

Managed validation:

- trim/normalize untuk pencarian duplicate;
- compare case-insensitive dalam company scope;
- duplicate diblokir melalui managed context.

Barcode tetap mengikuti constraint native Odoo.

## 4. Attribute dan Variant

### 4.1 Attribute master terpisah

Flow:

```text
1. Buat Attribute di Products → Atribut
2. Tambahkan values
3. Buka Product → Variants
4. Pilih Attribute dan existing values
5. Odoo membuat combinations native
```

Product form tidak membuat master Attribute mentah secara inline. CTA `Buat atribut` membuka master Attribute di tab baru agar draft Product tidak hilang.

Alasan:

- satu master `Ukuran`, bukan banyak Attribute bernama sama;
- values dapat dipakai lintas Product;
- creation mode konsisten;
- duplicate lebih mudah dikendalikan.

### 4.2 Creation mode

UI business label dan native value:

```text
Saat produk disimpan          → always
Saat digunakan dalam transaksi → dynamic
Tidak membuat varian          → no_variant
```

`create_variant` tidak boleh diubah setelah Attribute dipakai Product karena dapat mengubah identity combinations.

### 4.3 Combination limit

Managed preview menghitung perkalian values pada Attribute pembentuk variant.

Contoh:

```text
Warna: 5
Ukuran: 4
Bahan: 3
Total: 5 × 4 × 3 = 60 variants
```

Instant generation dibatasi 1.000 combinations agar satu penyimpanan tidak membuat ledakan SKU tanpa sengaja.

### 4.4 Harga normal variant

Harga normal memakai native formula:

```text
Template list price
+ product.template.attribute.value.price_extra
= Variant sales price
```

Contoh:

```text
Harga dasar             Rp100.000
Ukuran L extra          Rp0
Ukuran XL extra         Rp15.000

L  = Rp100.000
XL = Rp115.000
```

`price_extra` adalah per value pada Product, bukan harga universal Attribute Value. Nilai `XL` dapat memiliki tambahan berbeda pada Product lain.

### 4.5 Per-variant data

Managed variant editor mendukung:

- SKU;
- barcode;
- image;
- cost;
- weight;
- volume;
- On Hand;
- Forecast;
- active/archive.

On Hand dan Forecast tetap read-only.

## 5. Category

Category tetap hierarchy native:

```text
Makanan
└── Minuman
    └── Air Mineral
```

Field penting:

```text
parent_id
parent_path
complete_name
product_count
```

Managed rules:

- nama trim dan wajib;
- duplicate sibling case-insensitive diblokir;
- nama sama boleh ada di parent berbeda;
- parent selector mengecualikan diri dan subtree;
- recursion tetap divalidasi native;
- managed delete dimatikan.

Mengapa delete dimatikan:

- Product dan Accounting dapat merujuk Category;
- perubahan hierarchy memengaruhi reporting dan account defaults;
- pindahkan referensi lebih aman daripada menghapus histori.

Account income/expense Category hanya tampil untuk user Accounting.

## 6. Pricelist

### 6.1 Tujuan

Pricelist menyimpan harga contextual, misalnya:

```text
Retail IDR
Grosir
Reseller
Shopee IDR
Tokopedia IDR
Export USD
```

Pricelist bukan duplikasi Product. Channel berbeda tetap memakai Variant canonical yang sama.

Satu Product tidak boleh dibuat menjadi:

```text
Kaos Luma Shopee
Kaos Luma Tokopedia
Kaos Luma Website
```

Itu akan memecah SKU, barcode, procurement, dan stock.

### 6.2 Scope rule

Managed editor mendukung native scope:

```text
Semua produk       → 3_global
Kategori produk    → 2_product_category
Produk tertentu    → 1_product
Variant tertentu   → 0_product_variant
```

Target canonical:

```text
Category rule → categ_id
Product rule  → product_tmpl_id
Variant rule  → product_tmpl_id + product_id
```

`product_id` pada Pricelist Item adalah `product.product`.

### 6.3 Variant-specific price

Flow:

```text
1. Tambah aturan harga
2. Berlaku untuk: Variant tertentu
3. Pilih Product
4. Pilih Variant dari Product tersebut
5. Pilih metode harga
6. Simpan aturan
```

Selector Variant server-side difilter:

```text
product.product.product_tmpl_id = Product terpilih
```

Tanpa Product, selector Variant mengembalikan kosong. Tombol save nonaktif jika Product atau Variant belum lengkap.

Contoh:

```text
Pricelist: Shopee IDR

Luma Test Product (L)  = Rp120.000
Luma Test Product (XL) = Rp135.000
```

Data:

```text
applied_on = 0_product_variant
product_tmpl_id = Luma Test Product
product_id = Variant L atau XL
compute_price = fixed
```

### 6.4 Metode harga

```text
Harga tetap          → fixed
Diskon persentase    → percentage
Formula lanjutan     → formula
```

Formula native dapat memakai:

```text
base
base_pricelist_id
price_discount
price_surcharge
price_round
price_min_margin
price_max_margin
```

Rule juga mendukung:

```text
min_quantity
date_start
date_end
```

Gunakan rule umum lalu override target yang lebih spesifik. Contoh:

```text
Semua produk: list price + 8%
Kategori Elektronik: list price + 5%
Variant tertentu: fixed price Rp129.000
```

Pemilihan rule final tetap tanggung jawab native Odoo Pricelist engine.

### 6.5 Duplicate dan lifecycle

Duplicate Pricelist diblokir berdasarkan:

```text
normalized name + company + currency
```

Delete managed dimatikan. Gunakan `active=false` untuk archive agar order historis tetap memiliki referensi.

### 6.6 Omnichannel boundary

Current state:

- Pricelist dan variant-specific rule tersedia;
- Product/Variant canonical tersedia;
- connector marketplace belum tersedia.

Target connector:

```text
Channel/store instance
├── pricelist_id
├── warehouse_id
├── company_id
└── external Product/Variant mapping
```

Mapping ideal:

```text
Marketplace item ID  → product.template
Marketplace model ID → product.product
Store                 → product.pricelist
```

Saat order marketplace masuk, harga aktual harus disimpan sebagai snapshot pada Sales Order Line. Pricelist menjadi default/catalog source, bukan alat untuk menghitung ulang order historis.

Marketplace fee bukan Pricelist:

```text
Gross revenue       Rp100.000
Marketplace fee     Rp10.000
Net settlement      Rp90.000
```

Pricelist tetap Rp100.000. Fee dan payout dicatat pada settlement/accounting.

## 7. UoM

### 7.1 Tujuan

UoM mengonversi quantity dalam dimensi yang sama:

```text
Weight: kg, g, ton
Volume: L, ml, m³
Length: m, cm, mm, km
Unit: unit, lusin
```

Engine tetap native:

```text
uom.category
uom.uom
uom.uom._compute_quantity()
uom.uom._compute_price()
```

### 7.2 Category-centered editor

Managed action memakai `uom.category` sebagai parent:

```text
Kelompok: Volume
├── L  — satuan dasar
└── ml — 1 ml = 0,001 L
```

Satu kelompok wajib memiliki tepat satu satuan dasar aktif.

UI tidak meminta user mengisi:

```text
factor
factor_inv
uom_type
bigger
smaller
reference
```

User mengisi kalimat bisnis:

```text
1 [unit ini] = [jumlah] [satuan dasar]
```

Backend memetakan:

```text
managed_base_quantity = jumlah satuan dasar
factor = 1 / managed_base_quantity

quantity < 1 → smaller
quantity = 1 → reference
quantity > 1 → bigger
```

Contoh:

```text
1 ml = 0,001 L
managed_base_quantity = 0,001
factor = 1000
uom_type = smaller
```

### 7.3 Canonical baseline

Managed data menambahkan `ml` dan baseline rounding:

```text
unit = 1
kg   = 0,001
L    = 0,001
m    = 0,001
ml   = 1
```

`rounding` ditampilkan sebagai **Kuantitas minimum**, bukan jumlah digit desimal.

Contoh:

```text
L rounding 0,001 → quantity terkecil 0,001 L
ml rounding 1    → quantity terkecil 1 ml
```

### 7.4 Product UoM

Product memakai:

```text
uom_id    = Satuan stok & penjualan
uom_po_id = Satuan pembelian
```

Purchase UoM harus berada dalam Category yang sama. Selector managed memfilter Category tersebut; constraint native tetap menjadi validasi terakhir.

Contoh valid:

```text
Stok & penjualan: kg
Pembelian: ton
```

Contoh invalid:

```text
Stok & penjualan: kg
Pembelian: unit
```

### 7.5 Transaction lock

Setelah UoM dipakai transaksi, field berikut dikunci dari managed UI:

- conversion ratio;
- rounding/minimum quantity;
- Category;
- native type/factor.

Usage diperiksa pada:

```text
stock.move
stock.move.line
sale.order.line
purchase.order.line
account.move.line
```

Alasan: mengubah `1 ml` dari `0,001 L` menjadi `0,01 L` setelah transaksi akan mengubah makna quantity historis.

Jika salah:

```text
Archive satuan lama
→ buat satuan baru yang benar
→ gunakan satuan baru untuk transaksi berikutnya
```

Satuan dasar tidak dapat diarsipkan. Managed delete UoM dimatikan.

## 8. Tiga konsep yang tidak boleh dicampur

### 8.1 Variant kemasan

Barang yang stoknya per botol/kemasan:

```text
Product: Air Mineral
UoM: unit
Attribute: Isi kemasan
Variants: 250 ml, 500 ml, 1 L
```

Setiap ukuran memiliki SKU dan stock sendiri. Teks `250 ml` adalah identity Variant, bukan perintah konversi stock.

### 8.2 UoM transaksi

Barang curah yang stocknya satu volume:

```text
Product: Minyak curah
UoM stock: L
UoM transaksi: ml
Sale: 500 ml
Stock delta: 0,5 L
```

Di sini `ml` benar-benar quantity conversion.

### 8.3 Product packaging

Kemasan logistik dengan rasio per Product:

```text
Product A: 1 dus = 12 unit
Product B: 1 dus = 24 unit
```

Gunakan `product.packaging`, bukan UoM global bernama `Dus`, karena `Dus` tidak punya satu rasio universal.

## 9. Lifecycle dan archive policy

| Data | Managed delete | Pengganti |
|---|---:|---|
| Product | Tidak menjadi flow utama | Archive Product/Variant |
| Attribute value | Hindari setelah dipakai | Archive relation/value sesuai native rules |
| Category | Tidak | Pindahkan Product/reference |
| Pricelist | Tidak | `active=false` |
| Pricelist rule | Editor menandai inactive/remove via parent draft | Simpan parent secara atomic |
| UoM | Tidak | Archive conversion unit; base tetap aktif |
| Vendor price | Draft relation | Edit/archive melalui Product parent |

Tujuan archive: dokumen lama tetap dapat menampilkan nama, unit, harga source, dan relation yang dipakai saat transaksi dibuat.

## 10. Validation matrix

| Area | Validation managed |
|---|---|
| Product SKU | Duplicate normalized SKU dalam company scope diblokir |
| Attribute | Nama wajib, trim, duplicate case-insensitive diblokir |
| Attribute Value | Nama wajib, trim, duplicate per Attribute diblokir |
| Category | Nama wajib, trim, duplicate sibling diblokir |
| Pricelist | Nama wajib, trim, duplicate company+currency diblokir |
| Pricelist Variant Rule | Product dan Variant wajib; Variant harus milik Product terpilih |
| UoM Category | Nama wajib, duplicate diblokir, tepat satu base aktif |
| UoM | Nama/ratio/rounding positif, duplicate per Category diblokir |
| UoM history | Ratio/rounding/category dikunci setelah transaksi |

Native constraints dan ACL tetap berjalan setelah validation managed.

## 11. API atomicity

Nested relation dapat membuat atau mengubah child sebelum validation akhir parent selesai. Managed create/update/delete dibungkus database savepoint.

```text
Nested write berhasil → commit bersama request
Nested write gagal    → parent dan seluruh child mutation rollback
```

Tanpa boundary ini, duplicate UoM/Attribute/Pricelist Rule dapat mengembalikan error tetapi meninggalkan child parsial di database.

## 12. UX contract

### Product

Tabs:

```text
Ringkasan
Variants
Penjualan
Pembelian
Persediaan
Pajak & Accounting
```

### Attribute

Primary flow:

```text
Nama atribut
Cara pilihan ditampilkan
Cara varian dibuat
Pilihan nilai
```

Rare settings berada di `Pengaturan lanjutan`.

### Pricelist

Primary flow:

```text
Nama daftar harga
Mata uang
Perusahaan
Aktif
Aturan harga
```

Rule drawer membuka field sesuai scope dan method. Formula hanya tampil saat dipilih.

### UoM

Primary flow:

```text
Nama kelompok satuan
Satuan dasar
Satuan konversi
```

Equation bisnis selalu tampil agar user dapat memeriksa makna ratio sebelum save.

## 13. Operational examples

### 13.1 Variant price per channel

```text
Product: Kaos Luma
Variants:
- L
- XL

Pricelist Retail:
- L  Rp100.000
- XL Rp115.000

Pricelist Shopee:
- L  Rp108.000
- XL Rp123.000
```

Semua harga menunjuk Variant yang sama. Stock tetap satu per Variant.

### 13.2 Category-wide wholesale price

```text
Pricelist Grosir
Rule Category: Minuman
Method: Diskon 10%
Minimum: 24 unit
```

Tambahkan rule Variant hanya untuk pengecualian.

### 13.3 Bulk liquid

```text
Product: Minyak curah
Stock UoM: L
Purchase UoM: L
Sales line: 500 ml
Result: stock berkurang 0,5 L
```

### 13.4 Packaged liquid

```text
Product: Minyak Botol
Stock UoM: unit
Attribute: Isi kemasan
Variants:
- 500 ml
- 1 L
```

Menjual satu Variant 500 ml mengurangi satu unit Variant tersebut, bukan `0,5 L` dari Variant lain.

## 14. Current status dan next step

Selesai baseline:

- Product custom form;
- Attribute master;
- native Variant generation dan editor;
- per-value `price_extra`;
- Category managed form;
- Pricelist global/category/product/variant rules;
- UoM category-centered editor;
- canonical `ml`;
- API atomic nested writes.

Belum selesai:

- konsistensi seluruh label Product ke Bahasa Indonesia; beberapa label default masih English;
- bulk matrix untuk memasukkan harga semua Variant sekaligus;
- copy Pricelist;
- price change audit/publish workflow;
- marketplace store mapping dan sync status;
- Product Packaging managed editor;
- Sales end-to-end;
- full browser role/responsive QA.

Prioritas berikutnya untuk transaksi:

```text
Quotation
→ pilih product.product
→ gunakan customer/channel Pricelist
→ confirm
→ delivery
→ invoice
→ payment status
```

Prioritas berikutnya untuk omnichannel, saat connector benar-benar dimulai:

```text
Store mapping
→ Variant external mapping
→ price publish
→ order import
→ stock sync
→ fee/settlement accounting
```

Jangan menambah model channel atau field Product sebelum contract connector dan settlement disepakati.

## 15. Implementation map

```text
managed/products/models/product.py
managed/products/models/uom.py
managed/products/data/uom_data.xml
managed/products/views/actions.xml
managed/products/frontend/product-form.tsx
managed/products/frontend/variant-manager.tsx
managed/products/frontend/attribute-form.tsx
managed/products/frontend/attribute-values.tsx
managed/products/frontend/category-form.tsx
managed/products/frontend/pricelist-form.tsx
managed/products/frontend/pricelist-rules.tsx
managed/products/frontend/uom-form.tsx
managed/products/frontend/uom-units.tsx
managed/core/controllers/ui_api.py
frontend/scripts/managed-products-self-check.mjs
```
