import { Boxes, Building2, ChevronRight, HandCoins, Settings2, ShieldCheck, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import ActionPage from "@/views/action-page";
import { getSettingsSection, type SettingsSection } from "./settings-registry";

const icons = { general: Building2, users: Users, roles: ShieldCheck, sales: HandCoins, products: Boxes };

export default function SettingsShell() {
  const [sections, setSections] = useState<SettingsSection[]>([]);
  const [error, setError] = useState<string>();
  const location = useLocation();
  const navigate = useNavigate();
  const rootPath = location.pathname.split("/").slice(0, 3).join("/") || "/app/pengaturan";
  const parts = location.pathname.slice(rootPath.length).split("/").filter(Boolean);
  const mainSections = sections.filter((section) => section.placement === "main");
  const moduleSections = sections.filter((section) => section.placement === "advanced");
  const activeKey = parts[0] === "advanced" ? parts[1] : parts[0] || "general";
  const active = sections.find((section) => section.key === activeKey) || mainSections[0];
  useEffect(() => { api<{ sections: SettingsSection[] }>("/api/v1/settings").then((result) => setSections(result.sections)).catch((reason) => setError(reason.message)); }, []);
  const open = (section: SettingsSection) => navigate(section.placement === "advanced" ? `${rootPath}/advanced/${section.key}` : `${rootPath}/${section.key}`);
  if (error) return <div className="workspace-error"><strong>Pengaturan gagal dimuat</strong><span>{error}</span></div>;
  if (!active) return <div className="workspace-loading">Memuat pengaturan...</div>;
  const Component = getSettingsSection(active.key);
  const id = active.actionId || undefined;
  return <div className="toova-settings-workspace">
    <aside className="toova-settings-sidebar">
      <header><h1>Pengaturan</h1></header>
      <nav>{[...mainSections, ...moduleSections].map((section, index) => { const Icon = icons[section.key as keyof typeof icons] || Settings2; return <button key={section.key} type="button" className={`${active.key === section.key ? "active" : ""}${index === mainSections.length ? " module-start" : ""}`} onClick={() => open(section)}><Icon/><span><strong>{section.label}</strong></span><ChevronRight/></button>; })}</nav>
    </aside>
    <main className="toova-settings-content">
      <header className="toova-settings-content-header"><div><h2>{active.label}</h2></div>{active.readiness.status !== "ready" && active.readiness.message && <b className={active.readiness.status}>{active.readiness.message}</b>}</header>
      <div className="toova-settings-content-body">{Component ? <Component section={active} onBack={() => navigate(rootPath)}/> : id ? <ActionPage actionId={id} basePath={active.placement === "advanced" ? `${rootPath}/advanced/${active.key}` : `${rootPath}/${active.key}`}/> : <div className="workspace-error"><strong>{active.label}</strong><span>Renderer belum tersedia.</span></div>}</div>
    </main>
  </div>;
}
