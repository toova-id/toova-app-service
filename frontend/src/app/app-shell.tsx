import { Bell, ChevronDown, ChevronRight, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun } from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { findMenuByPath, findTrail, firstAction, useNavigation } from "./navigation";
import { useSession } from "./session";
import type { ServerNavigationItem } from "./types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { getNavigationIcon } from "@/features/feature-registry";
import { cn } from "@/lib/utils";

function initials(label: string) { return label.split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase(); }
export function AppShell() {
  const session = useSession();
  const navigation = useNavigation();
  const location = useLocation();
  const [expanded, setExpanded] = useState(localStorage.getItem("luma.sidebar.expanded") === "true");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openApps, setOpenApps] = useState<number[]>([]);
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("luma.theme");
    return saved ? saved === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const userInitials = initials(session.user.name);
  const activeMenu = findMenuByPath(navigation, location.pathname);
  const activeTrail = activeMenu ? findTrail(navigation, activeMenu.id) : [];

  useEffect(() => { localStorage.setItem("luma.sidebar.expanded", String(expanded)); }, [expanded]);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("luma.theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => { setOpenApps((items) => [...new Set([...items, ...activeTrail])]); }, [activeMenu?.id]);

  const toggleApp = (id: number) => setOpenApps((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id]);
  const renderChild = (item: ServerNavigationItem, depth = 0): JSX.Element | null => {
    const action = firstAction(item);
    if (!action) return null;
    const hasChildren = item.children.length > 0;
    return <div key={item.id}>
      <div className="luma-submenu-row" style={{ paddingLeft: `${12 + depth * 10}px` }}>
        <NavLink to={action.path!} className={cn("luma-submenu-link", activeTrail.includes(item.id) && "luma-submenu-link-active", item.id === activeMenu?.id && "luma-submenu-link-current")}>{item.label}</NavLink>
        {hasChildren && <button type="button" onClick={() => toggleApp(item.id)} aria-label={`Buka ${item.label}`}><ChevronRight className={cn("h-3 w-3 transition-transform", openApps.includes(item.id) && "rotate-90")}/></button>}
      </div>
      {hasChildren && openApps.includes(item.id) && <div>{item.children.map((child) => renderChild(child, depth + 1))}</div>}
    </div>;
  };

  return <div className={cn("luma-shell", expanded && "luma-sidebar-expanded")}>
    {mobileOpen && <button type="button" className="luma-mobile-backdrop" onClick={() => setMobileOpen(false)} aria-label="Tutup navigasi"/>}
    <aside className={cn("luma-sidebar", mobileOpen && "luma-sidebar-mobile-open")}>
      <NavLink to="/app" className="luma-brand" title="Luma"><span className="luma-brand-mark"/><strong>Luma</strong></NavLink>
      <nav className="luma-navigation" aria-label="Navigasi utama">
        {navigation.map((item) => {
          const action = firstAction(item); if (!action) return null;
          const Icon = getNavigationIcon(item.module, item.xmlid);
          const active = activeTrail.includes(item.id);
          const current = item.id === activeMenu?.id;
          const open = openApps.includes(item.id);
          return <div key={item.id} className="luma-nav-group">
            <div className={cn("luma-nav-row", active && "luma-nav-row-active", current && "luma-nav-row-current")}>
              <NavLink to={action.path!} title={item.label} onClick={() => setMobileOpen(false)}><span className="luma-nav-icon">{Icon ? <Icon/> : initials(item.label)}</span><span className="luma-nav-label">{item.label}</span></NavLink>
              {expanded && item.children.length > 0 && <button type="button" onClick={() => toggleApp(item.id)} aria-label={`Buka submenu ${item.label}`}><ChevronRight className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-90")}/></button>}
            </div>
            {expanded && open && item.children.length > 0 && <div className="luma-submenus">{item.children.map((child) => renderChild(child))}</div>}
          </div>;
        })}
      </nav>
      <button type="button" className="luma-sidebar-toggle" onClick={() => setExpanded((value) => !value)}>{expanded ? <PanelLeftClose/> : <PanelLeftOpen/>}<span>{expanded ? "Ringkas" : "Perluas"}</span></button>
    </aside>

    <div className="luma-main">
      <header className="luma-topbar">
        <Button className="md:hidden" variant="ghost" size="icon" onClick={() => setMobileOpen(true)}><Menu className="h-4 w-4"/></Button>
        <button type="button" className="luma-global-search"><Search/><span>Cari data atau perintah</span><kbd>Ctrl K</kbd></button>
        <div className="luma-user-tools"><Button variant="ghost" size="icon" onClick={() => setDark((value) => !value)} aria-label={dark ? "Gunakan mode terang" : "Gunakan mode gelap"}>{dark ? <Sun className="h-4 w-4"/> : <Moon className="h-4 w-4"/>}</Button><Button variant="ghost" size="icon" aria-label="Notifikasi"><Bell className="h-4 w-4"/></Button><DropdownMenu.Root><DropdownMenu.Trigger asChild><Button variant="ghost" className="luma-user-trigger"><Avatar className="h-7 w-7"><AvatarFallback>{userInitials}</AvatarFallback></Avatar><span>{session.user.name}</span><ChevronDown className="h-3 w-3"/></Button></DropdownMenu.Trigger><DropdownMenu.Portal><DropdownMenu.Content align="end" className="z-50 min-w-52 rounded-md border bg-card p-1 shadow-[var(--shadow-floating)]"><DropdownMenu.Label className="px-2 py-2 text-[11px] text-muted-foreground">{session.company.name}<br/>{session.user.login}</DropdownMenu.Label><DropdownMenu.Separator className="my-1 h-px bg-border"/><DropdownMenu.Item asChild><a href="/web/session/logout?redirect=/app" className="flex cursor-pointer items-center gap-2 rounded px-2 py-2 text-xs outline-none hover:bg-muted"><LogOut className="h-3.5 w-3.5"/>Keluar</a></DropdownMenu.Item></DropdownMenu.Content></DropdownMenu.Portal></DropdownMenu.Root></div>
      </header>
      <main className="workspace-content"><Outlet/></main>
    </div>
  </div>;
}
