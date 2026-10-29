import { registerManagedNavigation } from "@toova/app/managed-navigation";

registerManagedNavigation("stock", {
  label: "Persediaan",
  items: [
    { xmlid: "inventory.menu_deliveries", label: "Pengiriman" },
    { xmlid: "inventory.menu_operations", label: "Operasi Gudang", hidden: true },
  ],
});
