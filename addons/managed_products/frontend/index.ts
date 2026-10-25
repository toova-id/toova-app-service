import "./views";
import "./navigation";
import { registerActionFormView } from "@luma/views/view-registry";
import ProductForm from "./product-form";

registerActionFormView("managed_products.action_products", ProductForm);
registerActionFormView("sale.product_template_action", ProductForm);
