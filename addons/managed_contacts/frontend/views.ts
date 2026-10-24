import { registerActionView, registerModelView } from "@luma/views/view-metadata";

registerModelView("res.partner", {
  list: { columns: ["name", "phone", "email", "city", "country_id", "vat"] },
  form: {
    titleField: "name",
    sections: [
      { id: "identity", label: "Identitas", description: "Informasi utama pelanggan, vendor, atau kontak.", columns: 2, fields: ["image_1920", "company_type", "name", "parent_id", "function"] },
      { id: "contact", label: "Kontak", columns: 2, fields: ["email", "phone", "mobile", "website"] },
      { id: "address", label: "Alamat", description: "Alamat Indonesia maupun internasional.", columns: 2, fields: ["street", "street2", "city", "state_id", "zip", "country_id"] },
      { id: "tax", label: "Identitas pajak", columns: 2, fields: ["l10n_id_pkp", "vat", "l10n_id_nik", "l10n_id_tku", "l10n_id_buyer_document_type", "l10n_id_buyer_document_number", "l10n_id_tax_name", "l10n_id_tax_address", "l10n_id_kode_transaksi"] },
      { id: "commercial", label: "Komersial", columns: 2, fields: ["user_id", "property_product_pricelist", "property_payment_term_id", "property_supplier_payment_term_id", "property_purchase_currency_id"] },
      { id: "other", label: "Lainnya", columns: 2, fields: ["category_id", "lang", "tz", "comment"] },
    ],
  },
});

registerActionView("account.res_partner_action_supplier", { list: { columns: ["name", "phone", "email", "city", "country_id", "vat"] } });
