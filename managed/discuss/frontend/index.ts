import { registerClientAction, registerModuleIcon } from "@toova/features/feature-registry";
import { Inbox } from "lucide-react";
import InboxPage from "./inbox-page";

registerModuleIcon("mail", Inbox);
registerClientAction("managed.inbox", InboxPage);
