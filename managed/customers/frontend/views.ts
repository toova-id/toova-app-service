import { registerActionView } from "@luma/views/view-metadata";

registerActionView("customers.action_customers", {
  list: { columns: ["name", "phone", "email", "city", "country_id", "vat"] },
  form: { titleField: "name", sections: [
    { id: "identity", label: "Identitas pelanggan", columns: 2, fields: ["image_1920", "company_type", "name", "email", "phone", "mobile", "website", "lang"] },
    { id: "address", label: "Alamat utama", description: "Dipakai sebagai fallback jika alamat khusus belum dipilih.", columns: 2, fields: ["managed_address_text", "country_id", "state_id", "managed_indonesia_regency_id", "managed_indonesia_district_id", "managed_indonesia_village_id", "city", "zip"] },
    { id: "locations", label: "Alamat", columns: 1, fields: ["managed_address_ids"] },
    { id: "contacts", label: "Kontak/PIC", columns: 1, fields: ["child_ids"] },
    { id: "sales", label: "Penjualan & keuangan", columns: 2, fields: ["user_id", "property_product_pricelist", "property_payment_term_id"] },
    { id: "tax", label: "Pajak & Coretax", columns: 2, fields: ["l10n_id_pkp", "vat", "l10n_id_nik", "l10n_id_tku", "l10n_id_buyer_document_type", "l10n_id_buyer_document_number", "l10n_id_tax_name", "l10n_id_tax_address", "l10n_id_kode_transaksi"] },
    { id: "other", label: "Lainnya", columns: 2, fields: ["category_id", "comment"] },
  ] },
});
