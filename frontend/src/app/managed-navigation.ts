import type { ServerNavigationItem } from "./types";

interface ManagedNavigationItem { xmlid: string; label?: string }
interface ManagedNavigationDefinition { label?: string; items: ManagedNavigationItem[] }

const definitions = new Map<string, ManagedNavigationDefinition>();

export function registerManagedNavigation(module: string, definition: ManagedNavigationDefinition) { definitions.set(module, definition); }

function findByXmlid(items: ServerNavigationItem[], xmlid: string): ServerNavigationItem | undefined {
  for (const item of items) {
    if (item.xmlid === xmlid) return item;
    const child = findByXmlid(item.children, xmlid);
    if (child) return child;
  }
}

export function applyManagedNavigation(items: ServerNavigationItem[]): ServerNavigationItem[] {
  return items.map((root) => {
    const definition = root.module ? definitions.get(root.module) : undefined;
    if (!definition) return root;
    const children = definition.items.flatMap(({ xmlid, label }) => {
      const item = findByXmlid([root], xmlid);
      return item ? [{ ...item, label: label || item.label, children: [] }] : [];
    });
    return { ...root, label: definition.label || root.label, children };
  }).filter((item) => item.path || item.children.length);
}
