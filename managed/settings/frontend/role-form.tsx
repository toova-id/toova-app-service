import { Save, ShieldCheck } from "lucide-react";
import { Button } from "@toova/components/ui/button";
import { ManagedFormSection, ManagedFormShell } from "@toova/components/managed-form";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import type { CustomFormViewProps } from "@toova/views/view-registry";

export default function RoleSettingsForm({ schema, id, values, editing, saving, onEdit, onChange, onSave, onBack }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field]));
  const field = (name: string) => { const meta = fields[name]; if (!meta) return null; return <label><span>{meta.label}</span><div>{editing ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>; };
  const actions = (id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>);
  return <ManagedFormShell icon={<ShieldCheck/>} title={String(values.name || "Role baru")} subtitle="Role & hak akses" actions={actions} onBack={onBack} className="toova-settings-record"><ManagedFormSection title="Identitas"><div className="toova-settings-record-grid">{field("name")}{field("active")}{field("user_ids")}</div></ManagedFormSection><ManagedFormSection title="Hak akses">{field("grant_ids")}</ManagedFormSection></ManagedFormShell>;
}
