import "./navigation";
import "./views";
import { HandCoins } from "lucide-react";
import { registerModuleIcon } from "@toova/features/feature-registry";
import { registerFieldEditor } from "@toova/views/field-registry";
import { registerActionFormView } from "@toova/views/view-registry";
import { registerSettingsSection } from "@toova/features/settings/settings-registry";
import SaleOrderForm from "./sale-order-form";
import SaleOrderLines from "./sale-order-lines";
import SalesSettings from "./settings";

registerModuleIcon("sale", HandCoins);
registerModuleIcon("sales", HandCoins);
registerFieldEditor("managed_sale_order_lines", SaleOrderLines);
registerActionFormView("sales.action_quotations", SaleOrderForm);
registerActionFormView("sales.action_orders", SaleOrderForm);
registerSettingsSection("sales", SalesSettings);
