import { registerManagedNavigation } from "@luma/app/managed-navigation";

registerManagedNavigation("managed_products", {
  label: "Products",
  items: [
    { xmlid: "managed_products.menu_products", label: "Products" },
    { xmlid: "managed_products.menu_product_attributes", label: "Atribut" },
    { xmlid: "managed_products.menu_product_categories", label: "Kategori" },
    { xmlid: "managed_products.menu_product_pricelists", label: "Daftar Harga" },
    { xmlid: "managed_products.menu_product_uom", label: "Satuan" },
  ],
});
