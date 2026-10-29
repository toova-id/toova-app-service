import "./navigation";
import { PackageCheck } from "lucide-react";
import { registerClientAction, registerModuleIcon } from "@toova/features/feature-registry";
import { registerFieldEditor } from "@toova/views/field-registry";
import { registerActionFormView } from "@toova/views/view-registry";
import DeliveryForm from "./delivery-form";
import DeliveryLines from "./delivery-lines";
import WarehousePage from "./warehouse-page";

registerClientAction("managed.warehouse", WarehousePage);
registerActionFormView("inventory.action_deliveries", DeliveryForm);
registerFieldEditor("managed_stock_move_lines", DeliveryLines);
registerModuleIcon("stock", PackageCheck);
registerModuleIcon("inventory", PackageCheck);
