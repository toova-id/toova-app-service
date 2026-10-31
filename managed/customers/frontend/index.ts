import "../../directory/frontend/styles.css";
import "./views";
import { registerActionFormView } from "@toova/views/view-registry";
import CustomerForm from "./customer-form";

registerActionFormView("customers.action_customers", CustomerForm);
