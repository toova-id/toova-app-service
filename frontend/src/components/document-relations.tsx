import { ArrowLeft, ArrowUpRight, FileText, ReceiptText, Truck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLocation, useNavigate } from "react-router-dom";
import { findByActionXmlid, useNavigation } from "@/app/navigation";
import type { RelatedDocumentGroup } from "@/views/types";

export function DocumentBack({ onBack, label = "Kembali" }: { onBack: () => void; label?: string }) {
  return <Button type="button" variant="ghost" size="icon" onClick={onBack} aria-label={label}><ArrowLeft className="h-3.5 w-3.5"/></Button>;
}

export function DocumentRelations({ groups }: { groups: RelatedDocumentGroup[] }) {
  const navigation = useNavigation();
  const location = useLocation();
  const navigate = useNavigate();
  const existingTrail = Array.isArray(location.state?.managedTrail) ? location.state.managedTrail.filter((item: unknown): item is string => typeof item === "string") : [];
  const open = (path: string) => navigate(path, { state: { managedTrail: [`${location.pathname}${location.search}`, ...existingTrail] } });
  const available = groups.flatMap((group) => {
    const path = findByActionXmlid(navigation, group.actionXmlid)?.path;
    return path ? [{ ...group, path }] : [];
  });
  if (!available.length) return null;
  const icon = (key: string) => key === "deliveries" ? <Truck/> : key === "payments" ? <ReceiptText/> : <FileText/>;
  return <section className="toova-document-relations" aria-label="Dokumen terkait">
    {available.map((group) => <div key={group.key}><span>{group.label}</span><div>{group.items.map((item) => <button key={item.id} type="button" title={`${group.label}: ${item.label}${item.status ? ` · ${item.status}` : ""}`} aria-label={`Buka ${group.label} ${item.label}`} onClick={() => open(`${group.path}/${item.id}`)}>{icon(group.key)}<b>{item.label}</b><ArrowUpRight aria-hidden="true"/></button>)}</div></div>)}
  </section>;
}
