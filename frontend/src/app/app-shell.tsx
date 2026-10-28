import { Bell, ChevronDown, ChevronRight, LogOut, Menu, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun } from "lucide-react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState, type CSSProperties } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { findMenuByPath, findTrail, firstAction, flattenNavigationChildren, useNavigation } from "./navigation";
import { useSession } from "./session";
import type { ServerNavigationItem } from "./types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { getNavigationIcon } from "@/features/feature-registry";
import { cn } from "@/lib/utils";

function initials(label: string) { return label.split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase(); }
export function AppShell() {
  const session = useSession();
  const navigation = useNavigation();
  const location = useLocation();
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(localStorage.getItem("toova.sidebar.expanded") === "true");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openApps, setOpenApps] = useState<number[]>([]);
  const [inboxCounts, setInboxCounts] = useState({ messages: 0, mentions: 0, activities: 0, attention: 0 });
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("toova.theme");
    return saved ? saved === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const userInitials = initials(session.user.name);
  const activeMenu = findMenuByPath(navigation, location.pathname);
  const activeTrail = activeMenu ? findTrail(navigation, activeMenu.id) : [];
  const rootAction = (item: ServerNavigationItem) => item.children.length ? item.children.map(firstAction).find(Boolean) : firstAction(item);
  const inboxRoot = navigation.find((item) => item.module === "mail");
  const inboxAction = inboxRoot ? firstAction(inboxRoot) : undefined;

  useEffect(() => { localStorage.setItem("toova.sidebar.expanded", String(expanded)); }, [expanded]);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("toova.theme", dark ? "dark" : "light");
  }, [dark]);
  useEffect(() => { setOpenApps((items) => [...new Set([...items, ...activeTrail])]); }, [activeMenu?.id]);
  useEffect(() => {
    const refresh = () => api<typeof inboxCounts>("/api/v1/inbox/counts").then(setInboxCounts).catch(() => undefined);
    const changed = (event: Event) => setInboxCounts((event as CustomEvent<typeof inboxCounts>).detail);
    const realtime = (event: Event) => {
      const notifications = (event as CustomEvent<{ type: string }[]>).detail;
      if (notifications.some((notification) => notification.type.startsWith("mail."))) refresh();
    };
    refresh();
    const timer = window.setInterval(refresh, 30000);
    const visible = () => document.visibilityState === "visible" && refresh();
    document.addEventListener("visibilitychange", visible);
    window.addEventListener("toova:inbox-counts", changed);
    window.addEventListener("toova:realtime", realtime);
    return () => { clearInterval(timer); document.removeEventListener("visibilitychange", visible); window.removeEventListener("toova:inbox-counts", changed); window.removeEventListener("toova:realtime", realtime); };
  }, []);

  const toggleApp = (id: number) => setOpenApps((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id]);
  const renderChild = (item: ServerNavigationItem, depth = 0): JSX.Element | null => {
    const action = firstAction(item);
    if (!action) return null;
    const hasChildren = item.children.length > 0;
    const open = openApps.includes(item.id);
    const active = activeTrail.includes(item.id);
    const current = item.id === activeMenu?.id;
    const style = { "--menu-depth": depth } as CSSProperties;
    return <div key={item.id} className="toova-submenu-item">
      <div className={cn("toova-submenu-row", hasChildren && !item.path && "toova-submenu-folder-row", active && "toova-submenu-row-active", current && "toova-submenu-row-current")} style={style}>
        {item.path ? <NavLink to={item.path} className="toova-submenu-link" onClick={() => setMobileOpen(false)}><i/>{item.label}</NavLink> : <button type="button" className="toova-submenu-folder" onClick={() => toggleApp(item.id)} aria-expanded={open}><span>{item.label}</span><ChevronRight className={cn("transition-transform", open && "rotate-90")}/></button>}
        {item.path && hasChildren && <button type="button" className="toova-submenu-expand" onClick={() => toggleApp(item.id)} aria-label={`${open ? "Tutup" : "Buka"} submenu ${item.label}`} aria-expanded={open}><ChevronRight className={cn("transition-transform", open && "rotate-90")}/></button>}
      </div>
      {hasChildren && open && <div className="toova-submenu-branch">{item.children.map((child) => renderChild(child, depth + 1))}</div>}
    </div>;
  };

  return <div className={cn("toova-shell", expanded && "toova-sidebar-expanded")}>
    {mobileOpen && <button type="button" className="toova-mobile-backdrop" onClick={() => setMobileOpen(false)} aria-label="Tutup navigasi"/>}
    <aside className={cn("toova-sidebar", mobileOpen && "toova-sidebar-mobile-open")}>
      <NavLink to="/app" className="toova-brand" title="Toova"><span className="toova-brand-mark"/><strong>Toova</strong></NavLink>
      <nav className="toova-navigation" aria-label="Navigasi utama">
        <span className="toova-navigation-title">Menu utama</span>
        {navigation.map((item) => {
          const action = rootAction(item); if (!action) return null;
          const Icon = getNavigationIcon(item.module, item.xmlid);
          const active = activeTrail.includes(item.id);
          const current = item.id === activeMenu?.id;
          const open = openApps.includes(item.id);
          const children = flattenNavigationChildren(item.children);
          return <div key={item.id} className="toova-nav-group">
            <div className={cn("toova-nav-row", active && "toova-nav-row-active", current && "toova-nav-row-current")}>
              <NavLink to={action.path!} title={item.label} onClick={() => setMobileOpen(false)}><span className="toova-nav-icon">{Icon ? <Icon/> : initials(item.label)}</span><span className="toova-nav-label">{item.label}</span>{item.module === "mail" && inboxCounts.messages > 0 && <b className="toova-nav-badge">{inboxCounts.messages > 99 ? "99+" : inboxCounts.messages}</b>}</NavLink>
              {expanded && children.length > 0 && <button type="button" onClick={() => toggleApp(item.id)} aria-label={`${open ? "Tutup" : "Buka"} submenu ${item.label}`} aria-expanded={open}><ChevronRight className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-90")}/></button>}
            </div>
            {expanded && open && children.length > 0 && <div className="toova-submenus">{children.map((child) => renderChild(child))}</div>}
          </div>;
        })}
      </nav>
      <button type="button" className="toova-sidebar-toggle" onClick={() => setExpanded((value) => !value)}>{expanded ? <PanelLeftClose/> : <PanelLeftOpen/>}<span>{expanded ? "Ringkas" : "Perluas"}</span></button>
    </aside>

    <div className="toova-main">
      <header className="toova-topbar">
        <Button className="md:hidden" variant="ghost" size="icon" onClick={() => setMobileOpen(true)}><Menu className="h-4 w-4"/></Button>
        <button type="button" className="toova-global-search"><Search/><span>Cari data atau perintah</span><kbd>Ctrl K</kbd></button>
        <div className="toova-user-tools"><Button variant="ghost" size="icon" onClick={() => setDark((value) => !value)} aria-label={dark ? "Gunakan mode terang" : "Gunakan mode gelap"}>{dark ? <Sun className="h-4 w-4"/> : <Moon className="h-4 w-4"/>}</Button><Button variant="ghost" size="icon" className="toova-notification-button" aria-label={`Notifikasi${inboxCounts.attention ? `, ${inboxCounts.attention} perlu perhatian` : ""}`} onClick={() => inboxAction?.path && navigate(`${inboxAction.path}?view=${inboxCounts.mentions ? "mentions" : "activities"}`)}><Bell className="h-4 w-4"/>{inboxCounts.attention > 0 && <b>{inboxCounts.attention > 99 ? "99+" : inboxCounts.attention}</b>}</Button><DropdownMenu.Root><DropdownMenu.Trigger asChild><Button variant="ghost" className="toova-user-trigger"><Avatar className="h-7 w-7"><AvatarFallback>{userInitials}</AvatarFallback></Avatar><span>{session.user.name}</span><ChevronDown className="h-3 w-3"/></Button></DropdownMenu.Trigger><DropdownMenu.Portal><DropdownMenu.Content align="end" className="z-50 min-w-52 rounded-md border bg-card p-1 shadow-[var(--shadow-floating)]"><DropdownMenu.Label className="px-2 py-2 text-[11px] text-muted-foreground">{session.company.name}<br/>{session.user.login}</DropdownMenu.Label><DropdownMenu.Separator className="my-1 h-px bg-border"/><DropdownMenu.Item asChild><a href="/web/session/logout?redirect=/app" className="flex cursor-pointer items-center gap-2 rounded px-2 py-2 text-xs outline-none hover:bg-muted"><LogOut className="h-3.5 w-3.5"/>Keluar</a></DropdownMenu.Item></DropdownMenu.Content></DropdownMenu.Portal></DropdownMenu.Root></div>
      </header>
      <main className="workspace-content"><Outlet/></main>
    </div>
  </div>;
}
