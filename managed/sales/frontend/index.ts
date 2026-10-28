import "./navigation";
import "./views";
import { HandCoins } from "lucide-react";
import { registerModuleIcon } from "@luma/features/feature-registry";
import { registerModelFormView } from "@luma/views/view-registry";
import { registerSettingsSection } from "@luma/features/settings/settings-registry";
import SaleOrderForm from "./sale-order-form";
import SalesSettings from "./settings";

registerModuleIcon("sale", HandCoins);
registerModelFormView("sale.order", SaleOrderForm);
registerSettingsSection("sales", SalesSettings);
