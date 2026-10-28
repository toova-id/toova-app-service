import PartyForm from "../../directory/frontend/party-form";
import type { CustomFormViewProps } from "@toova/views/view-registry";

export default function VendorForm(props: CustomFormViewProps) {
  return <PartyForm {...props} kind="vendor"/>;
}
