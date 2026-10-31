import fs from "node:fs";

const model = fs.readFileSync(new URL("../../managed/sales/models/sale_order.py", import.meta.url), "utf8");
const form = fs.readFileSync(new URL("../../managed/sales/frontend/sale-order-form.tsx", import.meta.url), "utf8");
const lines = fs.readFileSync(new URL("../../managed/sales/frontend/sale-order-lines.tsx", import.meta.url), "utf8");
const actionPage = fs.readFileSync(new URL("../src/views/action-page.tsx", import.meta.url), "utf8");
const relations = fs.readFileSync(new URL("../src/components/document-relations.tsx", import.meta.url), "utf8");
for (const token of ["sales.action_quotations", "sales.action_orders", "managed_customer_many2one", "managed_sale_order_lines", "managed_discount_mode", "managed_discount_fixed", "action_create_managed_invoice", "picking_ids", "invoice_ids", "_check_managed_sales_contract", "_recompute_prices"]) if (!model.includes(token)) throw new Error(`managed sales contract missing ${token}`);
for (const token of ["Ringkasan", "Produk dan layanan", "Pengiriman", "Faktur", "Pengaturan", "DocumentRelations", "toova-sales-tabs", "toova-sales-state", "delivery_status", "invoice_status", "role=\"tooltip\""] ) if (!form.includes(token)) throw new Error(`managed sales form missing ${token}`);
for (const token of ["actionXmlid", "findByActionXmlid", "Dokumen terkait"]) if (!relations.includes(token)) throw new Error(`managed document relations missing ${token}`);
if (form.includes("Status proses")) throw new Error("document state must stay in the single compact strip");
if (!form.includes('section("Pelanggan"') || !form.includes('className="toova-sales-overview"')) throw new Error("sales summary must keep customer overview hierarchy");
for (const token of ["Tambah produk atau layanan", "Odoo mengisi deskripsi, satuan, pajak, dan harga", "relations/${field.name}/onchange", "toova-sale-line-subtotal", "managed_discount_mode", "managed_discount_fixed", "<del>"]) if (!lines.includes(token)) throw new Error(`managed sales line editor missing ${token}`);
if (!actionPage.includes("recordAvailable === false")) throw new Error("state-changing actions must return to scoped list");
if (lines.includes('managed-relation-editor-backdrop" role="presentation" onMouseDown')) throw new Error("sales drawer must not close from backdrop click");
if (!lines.includes("createPortal") || !lines.includes(", document.body)")) throw new Error("sales drawer must render outside form event tree");
console.log("managed sales self-check passed");
