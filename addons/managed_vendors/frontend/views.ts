import { registerActionView } from "@luma/views/view-metadata";

registerActionView("managed_vendors.action_vendors", {
  list: { columns: ["name", "phone", "email", "city", "country_id", "vat"] },
  form: { titleField: "name", sections: [
    { id: "identity", label: "Identitas vendor", columns: 2, fields: ["image_1920", "company_type", "name", "email", "phone", "mobile", "website", "lang"] },
    { id: "address", label: "Alamat utama", columns: 2, fields: ["managed_address_text", "country_id", "state_id", "managed_indonesia_regency_id", "managed_indonesia_district_id", "managed_indonesia_village_id", "city", "zip"] },
    { id: "locations", label: "Cabang & lokasi vendor", columns: 1, fields: ["managed_address_ids"] },
    { id: "contacts", label: "Kontak/PIC", columns: 1, fields: ["child_ids"] },
    { id: "purchase", label: "Pembelian & keuangan", columns: 2, fields: ["property_supplier_payment_term_id", "property_purchase_currency_id", "property_account_position_id", "receipt_reminder_email", "reminder_date_before_receipt"] },
    { id: "tax", label: "Pajak vendor", columns: 2, fields: ["l10n_id_pkp", "vat", "l10n_id_nik", "l10n_id_tku", "l10n_id_buyer_document_type", "l10n_id_buyer_document_number", "l10n_id_tax_name", "l10n_id_tax_address"] },
    { id: "bank", label: "Rekening pembayaran", columns: 1, fields: ["bank_ids"] },
    { id: "other", label: "Lainnya", columns: 2, fields: ["category_id", "comment"] },
  ] },
});
