import "../../directory/frontend/styles.css";
import "./views";
import { registerActionFormView } from "@toova/views/view-registry";
import VendorForm from "./vendor-form";

registerActionFormView("vendors.action_vendors", VendorForm);
