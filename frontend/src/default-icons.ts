import { Boxes, Building2, CalendarDays, Contact, Factory, FileText, HandCoins, MessagesSquare, PackageSearch, ShoppingCart, Users, Wrench } from "lucide-react";
import { registerModuleIcon } from "./features/feature-registry";

registerModuleIcon("mail", MessagesSquare);
registerModuleIcon("calendar", CalendarDays);
registerModuleIcon("contacts", Contact);
registerModuleIcon("crm", HandCoins);
registerModuleIcon("sale", HandCoins);
registerModuleIcon("account", FileText);
registerModuleIcon("project", Building2);
registerModuleIcon("purchase", ShoppingCart);
registerModuleIcon("stock", Boxes);
registerModuleIcon("mrp", Factory);
registerModuleIcon("maintenance", Wrench);
registerModuleIcon("repair", PackageSearch);
registerModuleIcon("hr", Users);
