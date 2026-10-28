import fs from "node:fs";

const source = fs.readFileSync(new URL("../src/app/managed-navigation.ts", import.meta.url), "utf8");
const icons = fs.readFileSync(new URL("../src/default-icons.ts", import.meta.url), "utf8");
const api = fs.readFileSync(new URL("../../managed/core/controllers/ui_api.py", import.meta.url), "utf8");
const sale = fs.readFileSync(new URL("../../managed/sales/frontend/navigation.ts", import.meta.url), "utf8");
for (const token of ["registerManagedNavigation", "applyManagedNavigation", "findByXmlid"]) if (!source.includes(token)) throw new Error(`managed navigation missing ${token}`);
for (const module of ["mail", "calendar", "contacts", "crm", "sale", "account", "project", "purchase", "stock", "mrp", "maintenance", "repair", "hr", "products", "customers", "vendors", "contact_persons", "people", "settings"]) if (!icons.includes(`registerModuleIcon("${module}"`)) throw new Error(`navigation icon missing ${module}`);
if (!api.includes("'module': menu.get('xmlid', '').partition('.')[0] or None")) throw new Error("navigation API must expose native and managed module ownership");
for (const xmlid of ["sale.menu_sale_quotations", "sale.menu_sale_order", "sale.menu_sale_order_invoice"]) if (!sale.includes(xmlid)) throw new Error(`sale navigation missing ${xmlid}`);
console.log("managed navigation self-check passed");
