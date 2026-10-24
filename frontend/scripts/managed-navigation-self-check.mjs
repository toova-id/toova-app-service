import fs from "node:fs";

const source = fs.readFileSync(new URL("../src/app/managed-navigation.ts", import.meta.url), "utf8");
const sale = fs.readFileSync(new URL("../../addons/sale/frontend/navigation.ts", import.meta.url), "utf8");
for (const token of ["registerManagedNavigation", "applyManagedNavigation", "findByXmlid"]) if (!source.includes(token)) throw new Error(`managed navigation missing ${token}`);
for (const xmlid of ["sale.menu_sale_quotations", "sale.menu_sale_order", "sale.menu_sale_order_invoice"]) if (!sale.includes(xmlid)) throw new Error(`sale navigation missing ${xmlid}`);
console.log("managed navigation self-check passed");
