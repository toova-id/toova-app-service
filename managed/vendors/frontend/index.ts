import "./views";
import { registerActionFormView } from "@luma/views/view-registry";
import VendorForm from "./vendor-form";

registerActionFormView("vendors.action_vendors", VendorForm);
