import { registerActionView } from "@luma/views/view-metadata";

registerActionView("managed_vendors.action_vendors", {
  list: { columns: ["name", "phone", "email", "city", "country_id", "vat"] },
  form: { titleField: "name", sections: [
    { id: "identity", label: "Identitas vendor", columns: 2, fields: ["image_1920", "company_type", "name", "email", "phone", "mobile", "website"] },
    { id: "address", label: "Alamat utama", columns: 2, fields: ["street", "street2", "city", "state_id", "zip", "country_id"] },
    { id: "locations", label: "Alamat penagihan dan penerimaan", columns: 1, fields: ["managed_address_ids"] },
    { id: "purchase", label: "Informasi pembelian", columns: 2, fields: ["property_supplier_payment_term_id", "property_purchase_currency_id"] },
    { id: "tax", label: "Pajak", columns: 2, fields: ["l10n_id_pkp", "vat", "l10n_id_nik", "l10n_id_tku", "l10n_id_buyer_document_type", "l10n_id_buyer_document_number", "l10n_id_tax_name", "l10n_id_tax_address"] },
    { id: "other", label: "Lainnya", columns: 2, fields: ["category_id", "lang", "comment"] },
  ] },
});
