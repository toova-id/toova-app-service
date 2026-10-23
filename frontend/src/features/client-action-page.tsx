import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { getClientAction, type ClientActionProps } from "./feature-registry";

export default function ClientActionPage({ actionId }: { actionId: number }) {
  const [action, setAction] = useState<ClientActionProps["action"]>();
  const [error, setError] = useState<string>();
  useEffect(() => { api<ClientActionProps["action"]>(`/api/v1/ui/client-actions/${actionId}`).then(setAction).catch((reason) => setError(reason.message)); }, [actionId]);
  if (error) return <div className="workspace-error"><strong>Aksi gagal dimuat</strong><span>{error}</span></div>;
  if (!action) return <div className="workspace-loading">Memuat fitur...</div>;
  const Component = getClientAction(action.tag);
  if (Component) return <Component action={action}/>;
  return <div className="workspace-error"><strong>{action.name}</strong><span>Fitur <code>{action.tag}</code> belum memiliki renderer Luma.</span></div>;
}
