import { createContext, useContext, type ReactNode } from "react";
import type { ServerNavigationItem } from "./types";

const NavigationContext = createContext<ServerNavigationItem[]>([]);
export function NavigationProvider({ items, children }: { items: ServerNavigationItem[]; children: ReactNode }) { return <NavigationContext.Provider value={items}>{children}</NavigationContext.Provider>; }
export function useNavigation() { return useContext(NavigationContext); }

export function firstAction(item: ServerNavigationItem): ServerNavigationItem | undefined {
  if (item.path) return item;
  for (const child of item.children) { const action = firstAction(child); if (action) return action; }
}

export function findMenuByPath(items: ServerNavigationItem[], pathname: string): ServerNavigationItem | undefined {
  let best: ServerNavigationItem | undefined;
  for (const item of items) {
    if (item.path && (pathname === item.path || pathname.startsWith(`${item.path}/`)) && (!best?.path || item.path.length > best.path.length)) best = item;
    const child = findMenuByPath(item.children, pathname);
    if (child && (!best?.path || (child.path?.length || 0) > best.path.length)) best = child;
  }
  return best;
}

export function findTrail(items: ServerNavigationItem[], menuId: number): number[] {
  for (const item of items) {
    if (item.id === menuId) return [item.id];
    const childTrail = findTrail(item.children, menuId);
    if (childTrail.length) return [item.id, ...childTrail];
  }
  return [];
}
