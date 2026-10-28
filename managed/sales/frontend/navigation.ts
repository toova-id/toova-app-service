import { registerManagedNavigation } from "@toova/app/managed-navigation";

registerManagedNavigation("sale", {
  label: "Penjualan",
  items: [
    { xmlid: "sales.menu_quotations", label: "Penawaran" },
    { xmlid: "sales.menu_orders", label: "Pesanan" },
  ],
});
