import PartyForm from "../../managed_directory/frontend/party-form";
import type { CustomFormViewProps } from "@luma/views/view-registry";

export default function CustomerForm(props: CustomFormViewProps) {
  return <PartyForm {...props} kind="customer"/>;
}
