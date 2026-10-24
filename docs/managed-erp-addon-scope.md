# Managed ERP Addon Scope

This repository carries only Odoo Community modules needed by the Indonesian managed ERP product. Modules listed below are product roots; their manifest dependency closure is retained automatically.

## Product roots

```text
Platform       managed_core web contacts calendar base_automation
Commercial     crm sale_management sale_stock sale_margin
Procurement    purchase_stock purchase_requisition_stock
Inventory      stock stock_account stock_picking_batch stock_dropshipping
               stock_landed_costs product_expiry delivery delivery_stock_picking_batch
Accounting     account account_payment account_debit_note account_edi
               account_edi_ubl_cii analytic account_lock
Indonesia      l10n_id l10n_id_efaktur l10n_id_efaktur_coretax
Human resource hr hr_contract hr_attendance hr_holidays hr_expense hr_recruitment
               hr_skills hr_recruitment_skills hr_presence hr_work_entry
               hr_work_entry_contract hr_work_entry_holidays
Projects       project hr_timesheet project_hr_expense project_purchase project_mrp
               sale_project sale_timesheet
Manufacturing  mrp mrp_account mrp_subcontracting mrp_subcontracting_account
               purchase_mrp sale_mrp mrp_landed_costs mrp_product_expiry
Maintenance    maintenance hr_maintenance repair mrp_repair
Payments       payment payment_custom
```

Payroll Indonesia, POS, Xendit/Midtrans providers, Indonesian delivery connectors, managed subscription, and product frontend remain custom work. `payment` and `account_payment` stay as framework modules.

Product roots describe packaged backend capability, not default end-user scope. Default visibility, capability profiles, field policy, Indonesian compliance gaps, and managed UI migration order are defined in [Managed ERP Product Scope Review](managed-erp-product-scope-review.md).

Excluded source includes foreign localizations, foreign payment providers, website/e-commerce, marketing, events, e-learning, surveys, hardware/IoT, themes, demo providers, and test-only addons.

## Change rule

Before removing or restoring a module, calculate complete `depends` closure from every retained `__manifest__.py`. Validate all dependencies exist, compile Python sources, then run install/update tests for every product root against PostgreSQL. Do not infer runtime safety from directory names alone.
