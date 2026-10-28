import { ArrowLeft, Save, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@luma/components/ui/button";
import { FieldEditor, FieldValue } from "@luma/views/field-registry";
import type { CustomFormViewProps } from "@luma/views/view-registry";

export default function RoleSettingsForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field]));
  const field = (name: string) => { const meta = fields[name]; if (!meta) return null; return <label><span>{meta.label}</span><div>{editing ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>; };
  return <div className="luma-settings-record"><header><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft/></Link></Button><div className="luma-settings-record-icon"><ShieldCheck/></div><div><h1>{String(values.name || "Role baru")}</h1></div><div>{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header><main><section><h2>Identitas</h2><div className="luma-settings-record-grid">{field("name")}{field("active")}{field("user_ids")}</div></section><section><h2>Hak akses</h2>{field("grant_ids")}</section></main></div>;
}
