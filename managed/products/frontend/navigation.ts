import { registerManagedNavigation } from "@luma/app/managed-navigation";

registerManagedNavigation("products", {
  label: "Products",
  items: [
    { xmlid: "products.menu_products", label: "Products" },
    { xmlid: "products.menu_product_attributes", label: "Atribut" },
    { xmlid: "products.menu_product_categories", label: "Kategori" },
    { xmlid: "products.menu_product_pricelists", label: "Daftar Harga" },
    { xmlid: "products.menu_product_uom", label: "Satuan" },
  ],
});
