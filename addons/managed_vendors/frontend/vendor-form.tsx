import PartyForm from "../../managed_directory/frontend/party-form";
import type { CustomFormViewProps } from "@luma/views/view-registry";

export default function VendorForm(props: CustomFormViewProps) {
  return <PartyForm {...props} kind="vendor"/>;
}
