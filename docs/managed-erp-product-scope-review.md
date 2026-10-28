# Managed ERP Product Scope Review — Indonesia First

Status: initial scope audit, 2026-10-24. Scope source: `scripts/test_managed_addon_scope.py`, retained manifests, model fields, views, security groups, and Indonesian localization code.

Current implementation decisions supersede recommendations in this audit where they differ. See [Managed ERP Product Architecture](managed-erp-product-architecture.md) for product boundaries and status, and [Managed Product Catalog](managed-product-catalog.md) for Product, Variant, Pricelist, and UoM contracts.

## 1. Executive decision

Do not expose Odoo addon scope as product scope.

Repository retains 60 product roots and 123 dependency-closure modules. Current local database installs 30 roots; 30 roots remain packaged but not installed. Upstream fields, menus, and settings are framework capability, not default product UX.

Managed product should ship capability profiles:

| Profile | Default | Purpose |
|---|---:|---|
| Core Commerce | yes | contacts, products, CRM, sales, purchase, inventory, invoicing, Indonesian tax |
| Service Delivery | optional | projects, tasks, timesheets, billable expenses |
| People | optional | employee directory, attendance, leave, expenses, recruitment |
| Manufacturing | optional | BoM, manufacturing orders, work orders, subcontracting |
| Asset Care | optional | maintenance and repair |
| Advanced Logistics | optional | lots/serials, expiry, packages, batch/wave, landed costs, dropship |
| Automation | admin opt-in | automated actions |
| Payment Collection | optional | transfer instructions; Indonesian gateways remain custom |

Default Indonesian SME workspace: Core Commerce. Do not install or reveal all optional profiles during first onboarding.

## 2. Product principles

1. Backend keeps ORM, ACL, record rules, business methods, compute, onchange, accounting, stock, and audit trail.
2. Managed UI contracts define allowed read/write fields and actions per action XML ID.
3. Frontend metadata defines layout and terminology. XML views remain migration fallback only.
4. Show user intent, not Odoo implementation detail.
5. Progressive disclosure: basic fields first; advanced fields only after capability setting or explicit “More options”.
6. Computed/technical fields may drive modifiers but must not become visible input.
7. Multi-company, multi-currency, foreign customer/vendor, country, language, fiscal position, Incoterm, and international address remain supported.
8. Indonesian defaults: `id_ID`, `Asia/Jakarta`, IDR, Indonesia, NPWP/NIK/TKU, Coretax, Indonesian chart/tax templates.
9. Never simplify accounting, tax, inventory valuation, stock traceability, or approvals by bypassing Odoo methods.

## 3. Findings requiring product action

### Critical — Indonesian compliance gaps

#### P0. PPh workflow absent

Evidence: localization chart contains PPh accounts, but retained modules contain no operational PPh withholding/e-Bupot workflow. Search finds only account names and generic withholding support.

Required product work:

- vendor/customer withholding tax profiles;
- PPh 21/22/23/25/26/4(2) applicability and rates;
- gross-up/non-gross-up handling;
- withholding certificates and e-Bupot export/integration;
- settlement, prepaid/payable posting, reconciliation, and reporting;
- effective-date rule versions and audit history.

Do not market accounting as Indonesia-complete before this exists and receives tax-domain review.

#### P0. Coretax generator has null-sensitive paths

Evidence:

- `SellerIDTKU = company.vat + company.partner.l10n_id_tku`;
- `BuyerIDTKU = partner.vat + partner.l10n_id_tku`;
- invoice line reads `product.l10n_id_product_code.code` and `uom.l10n_id_uom_code.code` directly.

Missing VAT/TKU/product code/UoM code can raise runtime errors or generate invalid XML. Current pre-download checks do not validate every dereferenced value.

Required:

- one preflight validator returning field-level errors;
- block generation when seller/buyer identity, product code, UoM code, invoice date, country mapping, tax code, or line data are missing;
- normalize NPWP/TIN/TKU before concatenation;
- make foreign-buyer rules explicit;
- regression fixtures for domestic PKP, domestic non-PKP, NIK, passport, foreign company, service, goods, luxury tax, credit note, kode 07/08/10.

#### P0. Tax labels/configuration need domain verification

Evidence: `tax_ST1` and `tax_PT1` are named `11%`, described `12%`, amount `11.0`; Coretax output uses 12% over 11/12 OtherTaxBase for transaction code 04. This may be intentional effective 11%, but setup and UI can mislead users.

Required:

- tax names describe legal calculation, for example “PPN 12% · DPP Nilai Lain 11/12”;
- effective-date versioning instead of ambiguous static labels;
- verify transaction-code default: legacy partner default is `01`, Coretax extension changes default to `04`;
- accountant-reviewed migration and posting tests.

#### P1. Localization defect

`l10n_id_efaktur.models.res_partner.ResConfigSettings.l10n_id_tax_name` is related to `l10n_id_tax_address`, not `l10n_id_tax_name`. Fix before exposing company tax setup.

### High — scope and UX risks

#### P1. Product roots are over-broad

60 roots include advanced modules unsuitable as universal defaults: work entries without payroll, presence via SMS, recruitment, skills, timesheet sale, subcontracting, landed cost on MO, dropship, batch/wave picking, expiry, automation, project-MRP, and repair.

Action: move from one root set to profile-specific root sets. Keep dependency closure per profile.

#### P1. Installed database is not representative

Only 30 of 60 roots are installed. Review and test gates against this DB miss attendance, contracts, leave, expenses, recruitment, timesheets, advanced logistics, subcontracting, dropship, landed costs, payment_custom, and others.

Action: create one disposable DB per profile plus one all-capabilities integration DB.

#### P1. Configuration surface leaks into daily users

Source contains 1,346 group-gated view references and many technical settings. Managed UI must not mirror every upstream setting.

Action: company admins get guided setup; operational users get task-oriented screens; technical configuration remains operator-only.

#### P1. Generic view support remains incomplete for operational flows

Current generic CRUD does not cover kanban, graph, pivot, activity views, barcode scanning, chatter/composer, accounting reconciliation, stock reservations/packages/lots, MRP timer/work-order interactions, attachment workflows, or rich report actions.

Action: classify actions as generic metadata, custom workflow, admin-only legacy bridge, or unsupported. Never silently render complex actions as weak generic forms.

## 4. Recommended default navigation

### Core Commerce

- Beranda
- Pelanggan & Vendor
- Produk
- Penjualan
  - Penawaran
  - Pesanan
  - Perlu Ditagih
- Pembelian
  - Permintaan Penawaran
  - Pesanan Pembelian
  - Perlu Ditagih
- Persediaan
  - Penerimaan
  - Pengiriman
  - Stok Saat Ini
  - Penyesuaian Stok
- Keuangan
  - Faktur Pelanggan
  - Tagihan Vendor
  - Pembayaran
  - Jurnal
  - e-Faktur/Coretax
  - Laporan inti
- Pengaturan

Hide by default: sales teams, UTM, campaign/source/medium, recurring revenue, packaging, route/rule internals, procurement groups, journal groups, reconciliation model templates, EDI internals, technical actions, and every settings menu irrelevant to enabled capabilities.

## 5. Field and flow policy by domain

### 5.1 Contacts (`res.partner`)

Default visible:

- entity type: company/person;
- name, email, phone/mobile;
- full international address: street, city, state, postal code, country;
- customer/vendor role inferred from transactions, not exposed as counters;
- language and currency preference under international options;
- tax identity section: PKP, NPWP/TIN, NIK/passport/other document, TKU, legal tax name/address, transaction code;
- bank accounts under payment section.

Advanced/conditional:

- fiscal position, payment terms, pricelist, salesperson, delivery/invoice child addresses;
- foreign document fields only when country/document type requires them;
- parent/child contacts only for organizations.

Hide from normal users:

- rank counters, commercial entity internals, message internals, signup/portal internals, UTM, technical company-dependent properties.

Validation:

- normalize NPWP/NIK/TIN; do not infer PKP solely from “VAT exists and country ID” without user confirmation;
- country required for tax/export and international orders;
- duplicate detection by normalized tax ID, email, and phone.

### 5.2 Products

Implementation status: managed Product, Attribute, Variant, Category, Pricelist, and UoM are now active. Canonical models and pricing/conversion engines remain native. See [Managed Product Catalog](managed-product-catalog.md).

Default visible:

- name, sell/purchase flags, goods/service type;
- internal SKU and barcode;
- sales price, cost, UoM, purchase UoM;
- category, sales/purchase taxes;
- track inventory switch;
- Coretax product code and UoM code when Indonesian taxable sales enabled.

Capability-gated:

- variants/attributes;
- lots/serials and expiry;
- packaging;
- routes, MTO, dropship;
- BoM/manufacturing;
- vendor pricelists;
- customer pricelists and multi-currency.

Hide:

- forecast and stock compute helpers, template/variant bridge fields, tax/cache helpers, procurement internals.

### 5.3 CRM

Default flow: New → Qualified → Proposal → Won/Lost.

Default fields: opportunity title, customer, contact data, expected revenue/currency, probability, salesperson, expected close, next activity, notes, source.

Optional: leads separate from opportunities, recurring revenue, scoring, teams, campaign/medium, properties.

Recommendation: disable lead mode and recurring revenue by default. One pipeline is easier for SMEs. Preserve international phone, language, currency, and country.

### 5.4 Sales

Default form:

- customer and invoice/delivery address;
- quotation/order date, validity, salesperson;
- optional customer reference;
- lines: product, description, quantity, UoM, unit price, discount if enabled, tax, subtotal;
- totals, payment term, notes;
- status and primary actions.

Advanced disclosure:

- pricelist/currency;
- fiscal position;
- warehouse, delivery policy, promised date;
- Incoterm and Incoterm location for international orders;
- analytic distribution/project;
- margin/cost only for authorized manager;
- tags/team/UTM/pro-forma.

Do not expose: invoice counters, transaction IDs, compute helpers, tax-country helpers, availability helper fields, route internals.

Flow: quotation → sent → confirmed order → delivery → invoice → payment. Keep Odoo onchange/compute for product autofill, pricelist, taxes, UoM, subtotal, totals, stock, invoice status.

### 5.5 Purchase

Default form:

- vendor, vendor reference, order date, expected arrival, buyer;
- lines: product, description, quantity, UoM, unit price, tax, subtotal;
- totals, payment term, notes;
- receipt and billing status.

Advanced:

- currency, fiscal position, Incoterm/location;
- destination/dropship address;
- reminder email;
- purchase agreement/tender;
- landed costs.

Default flow: RFQ → sent → PO → receipt → vendor bill → payment. Three-way control should compare ordered, received, and billed quantities. Vendor bill autofill remains backend-driven.

### 5.6 Inventory

Default:

- one warehouse with Stock, Vendors, Customers locations;
- receipts, deliveries, internal transfer, current stock, adjustment;
- picking fields: reference, source document, partner, scheduled date, source/destination, operations, responsible, note, status;
- operation lines: product, demand, done, UoM.

Capability-gated:

- multiple warehouses/locations;
- lots/serials;
- expiry;
- packages/owners;
- batch/wave;
- routes/push-pull/MTO/dropship;
- storage categories;
- signature;
- landed costs.

Never expose stock move/quant internals as normal CRUD. Use dedicated workflows because reservation, package, lot, scrap, return, and validation methods carry invariants.

### 5.7 Accounting and Indonesian tax

Default business screens:

- customer invoices/credit notes;
- vendor bills/refunds;
- incoming/outgoing payments;
- bank/cash journals;
- receivables/payables;
- tax report, P&L, balance sheet, general ledger;
- Coretax documents.

Default invoice fields:

- partner, invoice date, due/payment term, reference;
- currency only when non-IDR/multi-currency;
- invoice lines: product, description, quantity, UoM, price, discount, tax, subtotal;
- totals, payment status, notes;
- Indonesian tax section only when company/invoice qualifies.

Advanced accountant-only:

- journal, account, analytic distribution, fiscal position, tax details, lock dates, reversal, auto-post, reconciliation, exchange differences, EDI diagnostics.

Hide technical binary widgets and hashes. Do not expose generic JSON editors for tax totals or analytic distribution in production UX.

International support:

- foreign customer/vendor address and document type;
- transaction currency and exchange rate;
- fiscal positions/tax mapping;
- Incoterms;
- zero-rated/export treatment after tax review;
- UBL/CII import/export only when counterpart requires it.

### 5.8 Projects and timesheets

Default optional profile:

- project name, customer, manager, dates, members, description;
- task title, project, stage, assignees, deadline, priority, tags, description;
- timesheet date, employee, task/project, duration, description.

Disable by default: customer rating, email aliases, portal collaborators, recurring tasks, dependencies, milestones, task properties. Enable one at a time through profile settings.

### 5.9 HR

Employee default:

- work identity/contact, department, job, manager, work location, photo, status;
- private identity/address/bank/emergency records in HR-only section;
- Indonesian payroll identifiers require custom fields and strict ACL before payroll launch.

Attendance default: check in/out, worked duration, correction request, manager approval. Do not expose raw overtime internals.

Leave default: employee, type, date/range, duration, reason, attachment, status, approvers. Hide recurrence/calendar technical fields.

Expense default: employee, date, category, description, amount/currency, paid-by, receipt, analytic/project if enabled. Flow: draft → submitted → approved → posted → paid.

Recruitment default: candidate, job, contact, source, stage, recruiter, expected salary, availability, resume/attachments, interview. Hide UTM and scoring internals unless used.

Contracts/work entries: contract is useful; work entries mainly support payroll. Do not expose work-entry menus until Indonesian payroll exists.

### 5.10 Manufacturing

Optional profile only.

Default BoM: product, quantity/UoM, components. Operations/work centers optional.

Default MO: product, quantity, BoM, planned start, components, finished products, responsible, availability, status. Advanced: lots, byproducts, work orders, flexible consumption, subcontracting, expiry, landed cost, dependencies.

Use custom workflow views. Generic CRUD cannot safely represent reservations, consumption, production lots, timers, backorders, and scrap.

### 5.11 Maintenance and repair

Maintenance default: request, equipment, type, team/technician, schedule, duration, priority, description, stage.

Repair default: product, lot/serial, customer, quantity, schedule, operations/parts, fees, notes, totals, status. Advanced invoicing and stock integration remain methods, not direct field edits.

### 5.12 Calendar

Default: title, attendees, start/end, all-day, location/video URL, reminder, description.

Advanced collapsed section: privacy, show-as, tags, recurrence. Recurrence technical fields and invalid-email/follower/message internals must never appear as independent generic rows.

## 6. Capability matrix

| Capability | Default | Keep backend | UI strategy |
|---|---:|---:|---|
| Multi-company | no | yes | admin opt-in |
| Multi-currency | no, auto-enable on foreign currency | yes | contextual |
| Multiple pricelists | no | yes | sales setting |
| Discounts | yes | yes | role/setting |
| Multiple warehouses | no | yes | inventory setting |
| Multiple internal locations | no | yes | inventory setting |
| Lots/serials | no | yes | product/profile setting |
| Expiry | no | yes | requires lots |
| Packages/owners | no | yes | advanced logistics |
| Batch/wave | no | yes | advanced logistics |
| Dropship/MTO/routes | no | yes | advanced procurement |
| Landed costs | no | yes | advanced accounting/logistics |
| Analytic accounting | optional | yes | project/costing profile |
| CRM leads mode | no | yes | CRM setting |
| Project rating/portal | no | yes | service setting |
| Recurring tasks/dependencies/milestones | no | yes | separate toggles |
| Attendance/leave/expense/recruitment | optional | yes | People subprofiles |
| Work entries | hidden | yes | payroll prerequisite |
| MRP work orders/subcontracting | no | yes | manufacturing setting |
| e-Faktur Coretax | yes for Indonesian PKP | yes | guided compliance flow |
| Legacy e-Faktur range UI | hidden for Coretax | yes for migration | operator-only |
| UBL/CII | no | yes | international EDI opt-in |
| Automated actions | no | yes | operator/admin-only |

## 7. Managed UI migration classes

### Metadata-based generic

Suitable after contract definition:

- contacts;
- product/category/UoM basics;
- CRM opportunities and stages;
- purchase RFQ/PO;
- simple project/task forms;
- employees, contracts, attendance, leave, expense, applicant;
- maintenance requests/equipment;
- configuration reference lists.

### Custom workflow UI

Required:

- sales document (already custom);
- invoice/vendor bill and payment;
- bank reconciliation;
- stock picking, inventory adjustment, lot/package workflows;
- MRP production/work order;
- repair order;
- Coretax preflight/document generation;
- expense report approval;
- attendance kiosk;
- calendar recurrence editor.

### Legacy operator bridge until replaced

- accounting chart/journal/tax configuration;
- complex fiscal position and reconciliation models;
- route/rule/warehouse internals;
- automated actions;
- EDI diagnostics.

## 8. Delivery roadmap

### Phase 0 — compliance and scope gates

1. Fix Coretax null safety and tax-name defect.
2. Commission Indonesian tax review for PPN/Coretax defaults and PPh gap.
3. Split product roots into profiles.
4. Build profile test databases.
5. Add action inventory classification and block unsupported actions in managed navigation.

### Phase 1 — Core Commerce contracts

Order:

1. contacts + tax identity;
2. products + UoM + Coretax codes;
3. CRM;
4. sales;
5. purchase;
6. stock receipts/deliveries/current stock;
7. invoices/bills/payments;
8. Coretax documents.

For each action: Python contract, TS metadata/custom component, field/action allowlist, onchange tests, ACL tests, Indonesian labels, mobile/desktop UX test.

### Phase 2 — Service and People

Projects/tasks/timesheets, employee directory, attendance, leave, expenses, recruitment. Keep contracts/work entries hidden until payroll strategy decided.

### Phase 3 — Manufacturing and advanced logistics

MRP, repair, maintenance, traceability, expiry, packages, batch/wave, landed costs, dropship, subcontracting.

## 9. Release gates

- No managed route may use XML fallback without explicit allowlist.
- No editable computed field may be sent in write payload unless contract permits it.
- Every x2many row must support nested onchange where Odoo expects it.
- ACL and record-rule tests per role.
- Coretax preflight and XML fixture tests.
- Domestic and foreign customer/vendor fixtures.
- IDR and foreign-currency fixtures.
- Goods, services, taxable, zero-rated, exempt, luxury-tax fixtures.
- Full document chains: quote-to-cash, procure-to-pay, stock return, credit note, payment/reconciliation.
- Indonesian accountant sign-off before production accounting release.

## 10. Repository evidence summary

- Product roots: 60.
- Retained dependency closure: 123 modules.
- Current local DB installed roots: 30.
- Current local DB uninstalled roots: 30.
- Group-gated view references in major business modules: 1,346.
- Largest domains by declared fields: account ~1,039, stock ~634, MRP ~390, project ~286, HR ~257, leave ~236, sale ~215, product ~200.

These counts are complexity indicators, not product requirements. Managed contracts must deliberately expose a small business vocabulary over this backend.
