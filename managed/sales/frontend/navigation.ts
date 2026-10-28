import { registerManagedNavigation } from "@luma/app/managed-navigation";

registerManagedNavigation("sale", {
  label: "Penjualan",
  items: [
    { xmlid: "sale.menu_sale_quotations", label: "Penawaran" },
    { xmlid: "sale.menu_sale_order", label: "Pesanan Penjualan" },
    { xmlid: "sale.res_partner_menu", label: "Pelanggan" },
    { xmlid: "sale.menu_product_template_action", label: "Produk" },
    { xmlid: "sale.menu_sale_order_invoice", label: "Perlu Ditagih" },
    { xmlid: "sale.menu_sale_report", label: "Laporan" },
    { xmlid: "sale.menu_sale_general_settings", label: "Pengaturan" },
  ],
});
