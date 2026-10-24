import fs from "node:fs";

const source = fs.readFileSync(new URL("../../addons/managed_directory/models/directory.py", import.meta.url), "utf8");
for (const token of ["managed.partner.role", "managed.partner.address", "managed_vat_normalized", "_ensure_managed_role"]) if (!source.includes(token)) throw new Error(`managed directory missing ${token}`);
for (const addon of ["managed_customers", "managed_vendors", "managed_contacts", "managed_people"]) if (!fs.existsSync(new URL(`../../addons/${addon}/frontend/views.ts`, import.meta.url))) throw new Error(`missing ${addon}`);
console.log("managed directory self-check passed");
