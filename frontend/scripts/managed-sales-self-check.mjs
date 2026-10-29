import fs from "node:fs";

const model = fs.readFileSync(new URL("../../managed/sales/models/sale_order.py", import.meta.url), "utf8");
const form = fs.readFileSync(new URL("../../managed/sales/frontend/sale-order-form.tsx", import.meta.url), "utf8");
const lines = fs.readFileSync(new URL("../../managed/sales/frontend/sale-order-lines.tsx", import.meta.url), "utf8");
const actionPage = fs.readFileSync(new URL("../src/views/action-page.tsx", import.meta.url), "utf8");
for (const token of ["sales.action_quotations", "sales.action_orders", "managed_customer_many2one", "managed_sale_order_lines", "action_create_managed_invoice", "picking_ids", "invoice_ids", "_check_managed_sales_contract", "_recompute_prices"]) if (!model.includes(token)) throw new Error(`managed sales contract missing ${token}`);
for (const token of ["Pengaturan lanjutan", "Produk dan layanan", "Proses pesanan", "Buka pengiriman", "Buka faktur", "toova-document-state", "delivery_status", "invoice_status", "aria-current"] ) if (!form.includes(token)) throw new Error(`managed sales form missing ${token}`);
if (form.includes("Status proses")) throw new Error("document state must stay in the single compact strip");
if (!form.includes('<section className="toova-document-overview"><h2>Pelanggan</h2><div className="toova-document-overview-grid">')) throw new Error("customer heading must sit above both aligned overview columns");
for (const token of ["Tambah produk atau layanan", "Odoo mengisi deskripsi, satuan, pajak, dan harga", "relations/${field.name}/onchange"]) if (!lines.includes(token)) throw new Error(`managed sales line editor missing ${token}`);
if (!actionPage.includes("recordAvailable === false")) throw new Error("state-changing actions must return to scoped list");
console.log("managed sales self-check passed");
