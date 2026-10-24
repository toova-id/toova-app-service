import "./navigation";
import "./views";
import { HandCoins } from "lucide-react";
import { registerModuleIcon } from "@luma/features/feature-registry";
import { registerModelFormView } from "@luma/views/view-registry";
import SaleOrderForm from "./sale-order-form";

registerModuleIcon("sale", HandCoins);
registerModelFormView("sale.order", SaleOrderForm);
