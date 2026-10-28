import { registerModelView } from "@luma/views/view-metadata";

registerModelView("product.template", {
  list: { columns: ["image_128", "default_code", "name", "managed_product_kind", "categ_id", "list_price", "qty_available"] },
  form: {
    titleField: "name",
    sections: [
      { id: "identity", label: "Produk", description: "Identitas utama barang atau jasa.", columns: 2, fields: ["image_1920", "name", "default_code", "barcode", "managed_product_kind", "managed_track_inventory", "categ_id", "sale_ok", "purchase_ok", "active", "attribute_line_ids", "product_variant_ids"] },
      { id: "units", label: "Satuan", columns: 2, fields: ["uom_id", "uom_po_id", "weight", "volume"] },
      { id: "sales", label: "Penjualan", columns: 2, fields: ["list_price", "invoice_policy", "sale_delay", "taxes_id", "description_sale"] },
      { id: "purchase", label: "Pembelian", columns: 2, fields: ["standard_price", "purchase_method", "supplier_taxes_id", "seller_ids", "description_purchase"] },
      { id: "inventory", label: "Persediaan", description: "Kuantitas dihitung dari stock moves.", columns: 2, fields: ["tracking", "responsible_id", "route_ids", "qty_available", "virtual_available"] },
      { id: "tax", label: "Pajak & Accounting", columns: 2, fields: ["l10n_id_product_code", "property_account_income_id", "property_account_expense_id"] },
      { id: "description", label: "Catatan internal", columns: 1, fields: ["description"] },
    ],
  },
});
