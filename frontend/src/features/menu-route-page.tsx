import { useLocation } from "react-router-dom";
import { findMenuByPath, useNavigation } from "@/app/navigation";
import ActionPage from "@/views/action-page";
import ClientActionPage from "./client-action-page";

export default function MenuRoutePage() {
  const location = useLocation();
  const menu = findMenuByPath(useNavigation(), location.pathname);
  if (!menu?.actionId || !menu.actionModel) return <div className="workspace-error"><strong>Halaman tidak ditemukan</strong><span>Route ini tidak terhubung ke fitur aktif.</span></div>;
  if (menu.actionModel === "ir.actions.client") return <ClientActionPage actionId={menu.actionId}/>;
  return <ActionPage actionId={menu.actionId} basePath={menu.path!}/>;
}
