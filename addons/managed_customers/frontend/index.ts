import "./views";
import { registerActionFormView } from "@luma/views/view-registry";
import CustomerForm from "./customer-form";

registerActionFormView("managed_customers.action_customers", CustomerForm);
