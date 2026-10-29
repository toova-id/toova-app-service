# Managed ERP Agent Guide

Sebelum mengubah managed ERP, baca berurutan:

1. `docs/managed-erp-product-architecture.md`
2. `docs/managed-product-catalog.md` untuk Product, Variant, Category, Pricelist, UoM, atau Packaging
3. `docs/managed-erp-development-playbook.md` untuk pattern implementasi, checkpoint, next plan, acceptance criteria, dan blocker
4. model native Odoo serta managed contract/tests domain terkait

Aturan inti:

- Odoo tetap business engine; jangan tulis ulang accounting, stock, tax, pricing, UoM, procurement, compute, onchange, ACL, atau record rules.
- Gunakan canonical native model. Managed addons hanya menangani contract, workflow, validation, defaults, dedupe, capability, dan navigation.
- Action XML ID adalah anchor managed UI. Write allowlist dan endpoint permission wajib eksplisit.
- Relation sensitif wajib punya server-side domain. Nested writes wajib atomic melalui savepoint.
- Archive data historis; jangan delete jika transaksi dapat merujuk record.
- Update docs dalam commit yang sama jika domain ownership, workflow, invariant, permission, atau roadmap berubah.
- Jangan simpan secret, password, token, atau production credential dalam repository.

Urutan pekerjaan aktif:

```text
Catalog browser/role QA
→ Sales quotation slice dengan product.product dan Pricelist native
→ Sales confirmation/delivery/invoice/payment status
→ Directory duplicate hardening
→ Full Odoo test infrastructure
```

Minimum checks:

```bash
python3 scripts/test_managed_addon_scope.py
python3 scripts/test_managed_no_company_selector.py
cd frontend && npm run check
cd frontend && npm run build
git diff --check
```

Lihat `docs/managed-erp-development-playbook.md` untuk acceptance criteria dan runtime verification lengkap.
