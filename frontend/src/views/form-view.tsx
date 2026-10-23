import { ArrowLeft, Save } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { FieldEditor, FieldValue } from "./field-registry";
import { modifierActive } from "./modifiers";
import type { ActionSchema } from "./types";

export function FormView({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave, onButton }: { schema: ActionSchema; basePath: string; id?: number; values: Record<string, unknown>; editing: boolean; saving: boolean; onEdit: () => void; onChange: (name: string, value: unknown) => void; onSave: () => void; onButton: (name: string, type: "object" | "action") => void }) {
  const canWrite = id ? schema.form.write : schema.form.create;
  const status = schema.form.statusField;
  const statusOptions = status?.selection?.filter(([key]) => !schema.form.statusVisible.length || schema.form.statusVisible.includes(key)) ?? [];
  return <div className="workspace-form-view">
    <header className="workspace-control-panel"><div className="workspace-control-title flex items-center gap-2"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><h1>{id ? String(values.display_name || schema.form.title) : `Baru — ${schema.form.title}`}</h1></div><div/><div className="workspace-control-actions">{canWrite && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header>
    {(schema.form.buttons.length > 0 || statusOptions.length > 0) && <div className="workspace-form-commandbar"><div>{id && schema.form.buttons.filter((button) => !modifierActive(button.modifiers, "invisible", values)).map((button) => <Button key={`${button.type}:${button.name}:${button.label}`} variant={button.primary ? "default" : "outline"} onClick={() => onButton(button.name, button.type)}>{button.label}</Button>)}</div>{status && <ol>{statusOptions.map(([key, label]) => <li key={key} className={values[status.name] === key ? "active" : undefined}>{label}</li>)}</ol>}</div>}
    <div className="workspace-form-sheet">{schema.form.sections.map((section) => { const visibleFields = section.fields.filter((field) => field.name !== status?.name && !modifierActive(field.modifiers, "invisible", values)); if (!visibleFields.length) return null; return <section key={section.label}><h2>{section.label}</h2><div className="workspace-form-grid">{visibleFields.map((field) => { const readonly = Boolean(field.readonly) || modifierActive(field.modifiers, "readonly", values); const required = Boolean(field.required) || modifierActive(field.modifiers, "required", values); return <label key={field.name} title={field.help} className={["text", "html", "one2many", "many2many"].includes(field.type) ? "workspace-form-wide" : undefined}><span>{field.label}{required && <b>*</b>}</span><div className="workspace-form-control">{editing && !readonly ? <FieldEditor actionId={schema.id} field={field} value={values[field.name]} onChange={(value) => onChange(field.name, value)}/> : <FieldValue field={field} value={values[field.name]} record={values}/>}</div></label>; })}</div></section>; })}</div>
  </div>;
}
