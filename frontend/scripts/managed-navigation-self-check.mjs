import fs from "node:fs";

const source = fs.readFileSync(new URL("../src/app/managed-navigation.ts", import.meta.url), "utf8");
const icons = fs.readFileSync(new URL("../src/default-icons.ts", import.meta.url), "utf8");
const api = fs.readFileSync(new URL("../../managed/core/controllers/ui_api.py", import.meta.url), "utf8");
const sale = fs.readFileSync(new URL("../../managed/sales/frontend/navigation.ts", import.meta.url), "utf8");
for (const token of ["registerManagedNavigation", "applyManagedNavigation", "findByXmlid"]) if (!source.includes(token)) throw new Error(`managed navigation missing ${token}`);
for (const module of ["mail", "contacts", "sale", "products", "customers", "vendors", "contact_persons", "people", "settings"]) if (!icons.includes(`registerModuleIcon("${module}"`)) throw new Error(`navigation icon missing ${module}`);
for (const token of ["def _managed_action_ids", "_managed_action_ids(action_model)", "managed_actions.get(action_model, set())"]) if (!api.includes(token)) throw new Error(`navigation API must restrict menus to managed action anchors: ${token}`);
for (const xmlid of ["sales.menu_quotations", "sales.menu_orders"]) if (!sale.includes(xmlid)) throw new Error(`sale navigation missing ${xmlid}`);
console.log("managed navigation self-check passed");
