import { Bell, ChevronDown, LogOut, Menu, Search } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useState } from "react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { navigation } from "./features";
import { useSession } from "./session";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function AppShell() {
  const session = useSession();
  const [mobileOpen, setMobileOpen] = useState(false);
  const items = navigation.filter((item) => !item.module || session.modules.includes(item.module));
  const initials = session.user.name.split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase();

  return <div className="min-h-screen bg-background">
    <aside className={cn("fixed inset-y-0 left-0 z-40 w-64 border-r bg-slate-950 text-slate-200 transition-transform lg:translate-x-0", mobileOpen ? "translate-x-0" : "-translate-x-full")}>
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-5">
        <div className="grid h-9 w-9 place-items-center rounded-xl bg-cyan-400 font-black text-slate-950">E</div>
        <div><p className="font-semibold leading-none text-white">ERP Workspace</p><p className="mt-1 text-xs text-slate-400">Business workspace</p></div>
      </div>
      <nav className="space-y-1 p-3" aria-label="Navigasi utama">
        {items.map(({ label, path, icon: Icon }) => <NavLink key={path} to={path} end={path === "/app"} onClick={() => setMobileOpen(false)} className={({ isActive }) => cn("flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors", isActive ? "bg-cyan-400 text-slate-950" : "text-slate-300 hover:bg-white/10 hover:text-white")}><Icon className="h-4 w-4"/><span>{label}</span></NavLink>)}
      </nav>
      <div className="absolute inset-x-3 bottom-3 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-slate-400"><p className="font-medium text-slate-200">{session.company.name}</p><p className="mt-1">Ruang kerja aman</p></div>
    </aside>

    {mobileOpen && <button aria-label="Tutup navigasi" className="fixed inset-0 z-30 bg-slate-950/50 lg:hidden" onClick={() => setMobileOpen(false)} />}
    <div className="lg:pl-64">
      <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b bg-background/90 px-4 backdrop-blur md:px-6">
        <Button className="lg:hidden" variant="ghost" size="icon" onClick={() => setMobileOpen(true)} aria-label="Buka navigasi"><Menu className="h-5 w-5"/></Button>
        <div className="hidden max-w-md flex-1 items-center gap-2 rounded-lg border bg-muted/40 px-3 md:flex"><Search className="h-4 w-4 text-muted-foreground"/><input className="h-10 w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground" placeholder="Cari data atau perintah..." aria-label="Pencarian"/></div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label="Notifikasi"><Bell className="h-5 w-5"/></Button>
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild><Button variant="ghost" className="h-11 gap-2 px-2"><Avatar><AvatarFallback>{initials}</AvatarFallback></Avatar><span className="hidden text-left md:block"><span className="block text-sm leading-none">{session.user.name}</span><span className="mt-1 block text-xs font-normal text-muted-foreground">{session.company.name}</span></span><ChevronDown className="h-4 w-4 text-muted-foreground"/></Button></DropdownMenu.Trigger>
            <DropdownMenu.Portal><DropdownMenu.Content align="end" className="z-50 min-w-52 rounded-lg border bg-card p-1 shadow-panel"><DropdownMenu.Label className="px-2 py-2 text-xs text-muted-foreground">{session.user.login}</DropdownMenu.Label><DropdownMenu.Separator className="my-1 h-px bg-border"/><DropdownMenu.Item asChild><a href="/web/session/logout?redirect=/app" className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-2 text-sm outline-none hover:bg-muted"><LogOut className="h-4 w-4"/>Keluar</a></DropdownMenu.Item></DropdownMenu.Content></DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </header>
      <main className="p-4 md:p-6 lg:p-8"><Outlet/></main>
    </div>
  </div>;
}
