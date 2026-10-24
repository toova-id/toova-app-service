import { registerActionView } from "@luma/views/view-metadata";

registerActionView("managed_contacts.action_contact_persons", {
  list: { columns: ["name", "parent_id", "function", "email", "mobile"] },
  form: { titleField: "name", sections: [
    { id: "identity", label: "Kontak/PIC", description: "Orang yang terhubung ke pelanggan atau vendor.", columns: 2, fields: ["image_1920", "name", "parent_id", "function"] },
    { id: "contact", label: "Informasi kontak", columns: 2, fields: ["email", "phone", "mobile", "lang"] },
    { id: "notes", label: "Catatan", columns: 1, fields: ["comment"] },
  ] },
});
