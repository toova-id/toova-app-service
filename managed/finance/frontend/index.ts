import "./styles.css";
import "./navigation";
import { Landmark } from "lucide-react";
import { registerModuleIcon } from "@toova/features/feature-registry";
import { registerActionFormView } from "@toova/views/view-registry";
import InvoiceForm from "./invoice-form";
import PaymentForm from "./payment-form";

registerActionFormView("finance.action_customer_invoices", InvoiceForm);
registerActionFormView("finance.action_payments", PaymentForm);
registerModuleIcon("account", Landmark);
registerModuleIcon("finance", Landmark);
