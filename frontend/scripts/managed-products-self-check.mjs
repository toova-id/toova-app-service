import fs from "node:fs";

const contract = fs.readFileSync(new URL("../../addons/managed_products/models/product.py", import.meta.url), "utf8");
const views = fs.readFileSync(new URL("../../addons/managed_products/frontend/views.ts", import.meta.url), "utf8");
const form = fs.readFileSync(new URL("../../addons/managed_products/frontend/product-form.tsx", import.meta.url), "utf8");
const actions = fs.readFileSync(new URL("../../addons/managed_products/views/actions.xml", import.meta.url), "utf8");
for (const token of ["managed_sku_normalized", "managed_product_variants", "managed_product_kind", "managed_track_inventory", "managed_supplier_prices", "seller_ids", "property_account_income_id", "managed_products.action_products"]) if (!contract.includes(token)) throw new Error(`managed products missing ${token}`);
for (const token of ["Penjualan", "Pembelian", "Persediaan", "Pajak & Accounting", "seller_ids", "l10n_id_product_code"]) if (!form.includes(token) && !views.includes(token)) throw new Error(`managed product view missing ${token}`);
for (const token of ["menu_products_root", "menu_product_categories", "menu_product_pricelists", "menu_product_uom"]) if (!actions.includes(token)) throw new Error(`managed product navigation missing ${token}`);
console.log("managed products self-check passed");
