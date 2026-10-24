import "./views";
import { registerActionFormView } from "@luma/views/view-registry";
import ContactForm from "./contact-form";

registerActionFormView("managed_contacts.action_contact_persons", ContactForm);
