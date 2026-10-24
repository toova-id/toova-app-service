import fs from "node:fs";

const source = fs.readFileSync(new URL("../../addons/managed_directory/models/directory.py", import.meta.url), "utf8");
for (const token of ["managed.partner.role", "managed.partner.address", "managed_vat_normalized", "_ensure_managed_role"]) if (!source.includes(token)) throw new Error(`managed directory missing ${token}`);
for (const addon of ["managed_customers", "managed_vendors", "managed_contacts", "managed_people"]) if (!fs.existsSync(new URL(`../../addons/${addon}/frontend/views.ts`, import.meta.url))) throw new Error(`missing ${addon}`);
const navigation = fs.readFileSync(new URL("../../addons/managed_directory/views/navigation.xml", import.meta.url), "utf8");
for (const token of ["contacts.menu_contacts", "contacts.res_partner_menu_contacts", "contacts.res_partner_menu_config"]) if (!navigation.includes(token)) throw new Error(`managed navigation missing ${token}`);
for (const [addon, sequence] of [["managed_customers", "10"], ["managed_vendors", "20"], ["managed_contacts", "30"]]) {
  const actions = fs.readFileSync(new URL(`../../addons/${addon}/views/actions.xml`, import.meta.url), "utf8");
  if (!actions.includes('parent="contacts.menu_contacts"') || !actions.includes(`sequence="${sequence}"`)) throw new Error(`invalid ${addon} navigation`);
}
console.log("managed directory self-check passed");
