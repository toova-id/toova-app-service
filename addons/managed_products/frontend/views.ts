import { registerModelView } from "@luma/views/view-metadata";

registerModelView("product.template", {
  list: { columns: ["image_128", "default_code", "name", "detailed_type", "categ_id", "list_price", "qty_available"] },
  form: {
    titleField: "name",
    sections: [
      { id: "identity", label: "Produk", description: "Identitas utama barang atau jasa.", columns: 2, fields: ["image_1920", "name", "default_code", "barcode", "detailed_type", "categ_id", "sale_ok", "purchase_ok", "active"] },
      { id: "units", label: "Satuan", columns: 2, fields: ["uom_id", "uom_po_id", "weight", "volume"] },
      { id: "price", label: "Harga dan pajak", columns: 2, fields: ["list_price", "standard_price", "taxes_id", "supplier_taxes_id", "currency_id"] },
      { id: "inventory", label: "Persediaan", description: "Tampil untuk produk yang dikelola sebagai stok.", columns: 2, fields: ["tracking", "responsible_id", "qty_available", "virtual_available"] },
      { id: "tax", label: "Coretax", columns: 2, fields: ["l10n_id_product_code"] },
      { id: "description", label: "Deskripsi", columns: 1, fields: ["description_sale", "description_purchase", "description"] },
    ],
  },
});
