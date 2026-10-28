import fs from "node:fs";

const source = fs.readFileSync(new URL("../../managed/directory/models/directory.py", import.meta.url), "utf8");
for (const token of ["managed.partner.role", "managed.partner.address", "managed_vat_normalized", "_ensure_managed_role", "indonesia_village_id"]) if (!source.includes(token)) throw new Error(`managed directory missing ${token}`);
for (const addon of ["customers", "vendors", "contact_persons", "people"]) if (!fs.existsSync(new URL(`../../managed/${addon}/frontend/views.ts`, import.meta.url))) throw new Error(`missing ${addon}`);
const partyForm = fs.readFileSync(new URL("../../managed/directory/frontend/party-form.tsx", import.meta.url), "utf8");
for (const token of ["Alamat", "Kontak/PIC", "Pajak & Coretax", "managed_address_ids", "bank_ids"]) if (!partyForm.includes(token)) throw new Error(`party form missing ${token}`);
const contactForm = fs.readFileSync(new URL("../../managed/contact_persons/frontend/contact-form.tsx", import.meta.url), "utf8");
for (const token of ["Profil kontak", "Terhubung ke", "Informasi kontak"]) if (!contactForm.includes(token)) throw new Error(`contact form missing ${token}`);
const navigation = fs.readFileSync(new URL("../../managed/directory/views/navigation.xml", import.meta.url), "utf8");
for (const token of ["contacts.menu_contacts", "contacts.res_partner_menu_contacts", "contacts.res_partner_menu_config"]) if (!navigation.includes(token)) throw new Error(`managed navigation missing ${token}`);
for (const [addon, sequence] of [["customers", "10"], ["vendors", "20"], ["contact_persons", "30"]]) {
  const actions = fs.readFileSync(new URL(`../../managed/${addon}/views/actions.xml`, import.meta.url), "utf8");
  if (!actions.includes('parent="contacts.menu_contacts"') || !actions.includes(`sequence="${sequence}"`)) throw new Error(`invalid ${addon} navigation`);
}
if (!fs.existsSync(new URL("../../managed/indonesia_regions/data/regions.csv", import.meta.url))) throw new Error("Indonesia region data missing");
const registry = fs.readFileSync(new URL("../src/views/field-registry.tsx", import.meta.url), "utf8");
for (const token of ["setDraft", ">Batal<", ">Simpan<"]) if (!registry.includes(token)) throw new Error(`relation draft editor missing ${token}`);
console.log("managed directory self-check passed");
