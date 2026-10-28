import { registerActionView } from "@luma/views/view-metadata";

registerActionView("settings.action_company_profile", {
  form: { titleField: "name", sections: [
    { id: "identity", label: "Identitas perusahaan", columns: 2, fields: ["logo", "name", "email", "phone", "website", "vat", "currency_id"] },
    { id: "address", label: "Alamat perusahaan", columns: 2, fields: ["street", "street2", "city", "state_id", "zip", "country_id"] },
  ] },
});

registerActionView("settings.action_users", {
  list: { columns: ["name", "login", "active", "role_ids"] },
  form: { titleField: "name", sections: [
    { id: "identity", label: "Pengguna", columns: 2, fields: ["name", "login", "active", "lang", "tz", "role_ids"] },
  ] },
});

registerActionView("settings.action_roles", {
  list: { columns: ["name", "active", "user_ids"] },
  form: { titleField: "name", sections: [
    { id: "identity", label: "Role", columns: 2, fields: ["name", "active", "user_ids"] },
    { id: "permissions", label: "Feature & subfeature", description: "Pilih Tidak ada, Read, atau Write. Write selalu mencakup Read.", columns: 1, fields: ["grant_ids"] },
  ] },
});
