import type { LucideIcon } from "lucide-react";
import type { ComponentType, LazyExoticComponent } from "react";

export interface Company { id: number; name: string }
export interface Session {
  user: { id: number; name: string; login: string };
  company: Company;
  companies: Company[];
  modules: string[];
  csrfToken: string;
  realtimeUrl?: string;
}
export interface ServerNavigationItem {
  id: number;
  label: string;
  path: string | null;
  actionId: number | null;
  actionModel: "ir.actions.act_window" | "ir.actions.client" | null;
  xmlid: string;
  module: string | null;
  children: ServerNavigationItem[];
}
export interface NavigationItem {
  label: string;
  path: string;
  icon: LucideIcon;
  module?: string;
}
export interface FeatureRoute {
  path: string;
  component: LazyExoticComponent<ComponentType>;
  module?: string;
}
