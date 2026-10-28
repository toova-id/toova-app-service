import { registerActionView, registerModelView } from "@luma/views/view-metadata";

registerModelView("sale.order", {
  list: {
    columns: [
      { name: "name", label: "Nomor" },
      "partner_id",
      { name: "date_order", label: "Tanggal" },
      "user_id",
      "amount_total",
      { name: "state", label: "Status", widget: "badge" },
    ],
  },
  form: {
    titleField: "name",
    sections: [
      {
        id: "customer",
        label: "Pelanggan",
        description: "Identitas pelanggan dan alamat transaksi.",
        columns: 2,
        fields: ["partner_id", "client_order_ref", "partner_invoice_id", "partner_shipping_id"],
      },
      {
        id: "order",
        label: "Detail pesanan",
        description: "Tanggal, penanggung jawab, harga, dan ketentuan transaksi.",
        columns: 3,
        fields: ["date_order", "validity_date", "commitment_date", "user_id", "team_id", "company_id", "pricelist_id", "payment_term_id", "fiscal_position_id"],
      },
      {
        id: "lines",
        label: "Item pesanan",
        description: "Produk, kuantitas, harga, diskon, dan pajak.",
        columns: 1,
        fields: ["order_line"],
      },
      {
        id: "notes",
        label: "Catatan",
        columns: 1,
        fields: ["note"],
      },
    ],
  },
});

registerActionView("sale.action_quotations_with_onboarding", {
  list: { columns: [{ name: "name", label: "Penawaran" }, "partner_id", "create_date", "user_id", "amount_total", { name: "state", widget: "badge" }] },
});
registerActionView("sale.action_quotations", {
  list: { columns: [{ name: "name", label: "Penawaran" }, "partner_id", "create_date", "user_id", "amount_total", { name: "state", widget: "badge" }] },
});
