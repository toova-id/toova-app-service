import { registerManagedNavigation } from "@luma/app/managed-navigation";

registerManagedNavigation("managed_products", {
  label: "Products",
  items: [
    { xmlid: "managed_products.menu_products", label: "Products" },
    { xmlid: "managed_products.menu_product_attributes", label: "Attributes" },
    { xmlid: "managed_products.menu_product_categories", label: "Categories" },
    { xmlid: "managed_products.menu_product_pricelists", label: "Pricelists" },
    { xmlid: "managed_products.menu_product_uom", label: "Units of Measure" },
  ],
});
