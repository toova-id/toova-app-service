import "./views";
import "./navigation";
import { registerFieldEditor, registerFieldRenderer } from "@luma/views/field-registry";
import { registerActionFormView } from "@luma/views/view-registry";
import AttributeForm from "./attribute-form";
import { AttributeValuesEditor, AttributeValuesValue } from "./attribute-values";
import ProductForm from "./product-form";

registerFieldEditor("managed_attribute_values", AttributeValuesEditor);
registerFieldRenderer("managed_attribute_values", AttributeValuesValue);
registerActionFormView("managed_products.action_product_attributes", AttributeForm);
registerActionFormView("managed_products.action_products", ProductForm);
registerActionFormView("sale.product_template_action", ProductForm);
