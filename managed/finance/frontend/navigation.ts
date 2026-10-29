import { registerManagedNavigation } from "@toova/app/managed-navigation";

registerManagedNavigation("account", {
  label: "Keuangan",
  items: [
    { xmlid: "finance.menu_customer_invoices", label: "Faktur Pelanggan" },
    { xmlid: "finance.menu_payments", label: "Pembayaran" },
  ],
});
