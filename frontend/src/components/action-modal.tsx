import { useEffect, useMemo, useState } from "react";
import { X } from "lucide-react";
import { api, apiMutation } from "@/lib/api";
import { Button } from "./ui/button";
import { FieldEditor } from "@/views/field-registry";
import type { FieldSchema } from "@/views/types";

export interface WindowAction {
  type: "ir.actions.act_window";
  name?: string;
  res_model: string;
  res_id?: number | false;
  target?: string;
  views?: [number | false, string][];
  context?: Record<string, unknown> | string;
}
interface Schema { title: string; fields: FieldSchema[]; buttons: { name: string; label: string; type: "object" | "action"; primary: boolean }[] }

export function ActionModal({ action, onClose, onDone }: { action: WindowAction; onClose: () => void; onDone: () => void }) {
  const [schema, setSchema] = useState<Schema>();
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string>();
  const payload = useMemo(() => encodeURIComponent(JSON.stringify(action)), [action]);
  useEffect(() => { api<{ schema: Schema; values: Record<string, unknown> }>(`/api/v1/ui/window-action?payload=${payload}`).then((response) => { setSchema(response.schema); setValues(response.values); }).catch((reason) => setError(reason.message)); }, [payload]);
  async function run(name: string, type: "object" | "action") {
    try {
      const response = await apiMutation<{ result: unknown }>("/api/v1/ui/window-action/run", "POST", { action, values, name, type });
      if (response.result && typeof response.result === "object" && (response.result as { type?: string }).type === "ir.actions.act_window_close") onClose(); else onDone();
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  }
  return <div className="toova-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="toova-modal" role="dialog" aria-modal="true" aria-label={action.name || "Dialog"}><header><h2>{schema?.title || action.name || "Dialog"}</h2><Button variant="ghost" size="icon" onClick={onClose}><X className="h-4 w-4"/></Button></header>{error ? <div className="toova-modal-error">{error}</div> : !schema ? <div className="toova-modal-loading">Memuat...</div> : <><main>{schema.fields.map((field) => <label key={field.name}><span>{field.label}{field.required && <b>*</b>}</span><div><FieldEditor actionId={0} field={field} value={values[field.name]} onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))}/></div></label>)}</main><footer>{schema.buttons.map((button) => <Button key={`${button.type}:${button.name}`} variant={button.primary ? "default" : "outline"} onClick={() => run(button.name, button.type)}>{button.label}</Button>)}<Button variant="ghost" onClick={onClose}>Tutup</Button></footer></>}</section></div>;
}
