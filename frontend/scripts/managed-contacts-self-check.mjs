import fs from "node:fs";

const contract = fs.readFileSync(new URL("../../addons/managed_contacts/models/res_partner.py", import.meta.url), "utf8");
const views = fs.readFileSync(new URL("../../addons/managed_contacts/frontend/views.ts", import.meta.url), "utf8");
for (const token of ["managed_vat_normalized", "managed_nik_normalized", "write_fields", "contacts.action_contacts"]) if (!contract.includes(token)) throw new Error(`managed contacts missing ${token}`);
for (const token of ["Identitas pajak", "Alamat", "property_product_pricelist"]) if (!views.includes(token)) throw new Error(`managed contact view missing ${token}`);
console.log("managed contacts self-check passed");
