import PartyForm from "../../directory/frontend/party-form";
import type { CustomFormViewProps } from "@toova/views/view-registry";

export default function CustomerForm(props: CustomFormViewProps) {
  return <PartyForm {...props} kind="customer"/>;
}
