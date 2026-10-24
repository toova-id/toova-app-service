import { registerActionView } from "@luma/views/view-metadata";

registerActionView("managed_customers.action_customers", {
  list: { columns: ["name", "phone", "email", "city", "country_id", "vat"] },
  form: { titleField: "name", sections: [
    { id: "identity", label: "Identitas pelanggan", columns: 2, fields: ["image_1920", "company_type", "name", "email", "phone", "mobile", "website"] },
    { id: "address", label: "Alamat utama", columns: 2, fields: ["street", "street2", "city", "state_id", "zip", "country_id"] },
    { id: "locations", label: "Alamat tagihan dan pengiriman", columns: 1, fields: ["managed_address_ids"] },
    { id: "sales", label: "Informasi penjualan", columns: 2, fields: ["user_id", "property_product_pricelist", "property_payment_term_id"] },
    { id: "tax", label: "Pajak dan Coretax", columns: 2, fields: ["l10n_id_pkp", "vat", "l10n_id_nik", "l10n_id_tku", "l10n_id_buyer_document_type", "l10n_id_buyer_document_number", "l10n_id_tax_name", "l10n_id_tax_address", "l10n_id_kode_transaksi"] },
    { id: "other", label: "Lainnya", columns: 2, fields: ["category_id", "lang", "comment"] },
  ] },
});
