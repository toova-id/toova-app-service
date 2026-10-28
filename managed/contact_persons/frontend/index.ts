import "./views";
import { registerActionFormView } from "@toova/views/view-registry";
import ContactForm from "./contact-form";

registerActionFormView("contact_persons.action_contact_persons", ContactForm);
