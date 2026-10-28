import { registerActionView } from "@toova/views/view-metadata";

registerActionView("sales.action_quotations", {
  list: {
    columns: [
      { name: "name", label: "Nomor" }, "partner_id", { name: "date_order", label: "Tanggal" },
      { name: "validity_date", label: "Berlaku sampai" }, "amount_total", { name: "state", label: "Status", widget: "badge" },
    ],
  },
});

registerActionView("sales.action_orders", {
  list: {
    columns: [
      { name: "name", label: "Nomor" }, "partner_id", { name: "date_order", label: "Tanggal" },
      { name: "delivery_status", label: "Pengiriman", widget: "badge" }, "amount_total", { name: "invoice_status", label: "Tagihan", widget: "badge" },
    ],
  },
});
