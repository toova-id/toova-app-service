import fs from "node:fs";

const contract = fs.readFileSync(new URL("../../addons/managed_products/models/product.py", import.meta.url), "utf8");
const views = fs.readFileSync(new URL("../../addons/managed_products/frontend/views.ts", import.meta.url), "utf8");
for (const token of ["managed_sku_normalized", "managed_product_variants", "write_fields", "sale.product_template_action"]) if (!contract.includes(token)) throw new Error(`managed products missing ${token}`);
for (const token of ["Harga dan pajak", "Persediaan", "l10n_id_product_code"]) if (!views.includes(token)) throw new Error(`managed product view missing ${token}`);
console.log("managed products self-check passed");
