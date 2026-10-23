import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";

export interface ClientActionProps {
  action: { id: number; name: string; tag: string; target: string; params: Record<string, unknown>; model?: string };
}
const clientActions = new Map<string, ComponentType<ClientActionProps>>();
const moduleIcons = new Map<string, LucideIcon>();
const menuIcons = new Map<string, LucideIcon>();

export function registerClientAction(tag: string, component: ComponentType<ClientActionProps>) { clientActions.set(tag, component); }
export function getClientAction(tag: string) { return clientActions.get(tag); }
export function registerModuleIcon(module: string, icon: LucideIcon) { moduleIcons.set(module, icon); }
export function registerMenuIcon(xmlid: string, icon: LucideIcon) { menuIcons.set(xmlid, icon); }
export function getNavigationIcon(module: string | null, xmlid: string) { return menuIcons.get(xmlid) || (module ? moduleIcons.get(module) : undefined); }
