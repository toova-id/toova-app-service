import { ArrowLeft, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@luma/components/ui/button";
import { FieldEditor, FieldValue, registerFieldEditor, registerFieldRenderer } from "@luma/views/field-registry";
import type { CustomFormViewProps } from "@luma/views/view-registry";
import type { PermissionFeature } from "@luma/features/settings/settings-registry";
import { useEffect, useMemo, useState } from "react";
import { api } from "@luma/lib/api";

export function RoleMatrix({ actionId, value, onChange, disabled = false }: { actionId: number; value: unknown; onChange: (value: unknown) => void; disabled?: boolean }) {
  const [features, setFeatures] = useState<PermissionFeature[]>([]);
  useEffect(() => { api<{ features: PermissionFeature[] }>("/api/v1/settings").then((result) => setFeatures(result.features)); }, [actionId]);
  const rows = Array.isArray(value) ? value as Record<string, unknown>[] : [];
  const levels = useMemo(() => Object.fromEntries(rows.map((row) => [String(row.permission_key), String(row.level)])), [rows]);
  const setLevel = (permissionKey: string, level: string) => {
    const existing = rows.find((row) => row.permission_key === permissionKey);
    const next = rows.filter((row) => row.permission_key !== permissionKey);
    if (level !== "none") next.push({ ...(existing || {}), permission_key: permissionKey, level });
    onChange(next);
  };
  return <div className="luma-role-matrix">{features.map((feature) => <section key={feature.key}><header><h3>{feature.label}</h3><div>{[["none", "Kosongkan"], ["read", "Semua Read"], ["write", "Semua Write"]].map(([level, label]) => <button key={level} type="button" disabled={disabled} onClick={() => { const existingMap = Object.fromEntries(rows.map((row) => [String(row.permission_key), row])); const keys = new Set(feature.permissions.map((permission) => permission.key)); const rest = rows.filter((row) => !keys.has(String(row.permission_key))); const added = level === "none" ? [] : feature.permissions.map((permission) => ({ ...(existingMap[permission.key] || {}), permission_key: permission.key, level })); onChange([...rest, ...added]); }}>{label}</button>)}</div></header>{feature.permissions.map((permission) => { const current = levels[permission.key] || "none"; return <div key={permission.key} className="luma-role-row"><span>{permission.label}</span><div>{[["none", "Tidak ada"], ["read", "Read"], ["write", "Write"]].map(([level, label]) => <button key={level} type="button" className={current === level ? "active" : undefined} disabled={disabled} onClick={() => setLevel(permission.key, level)}>{label}</button>)}</div></div>; })}</section>)}</div>;
}

registerFieldEditor("managed_permission_matrix", ({ actionId, value, onChange }) => <RoleMatrix actionId={actionId} value={value} onChange={onChange}/>);
registerFieldRenderer("managed_permission_matrix", ({ value }) => <span>{Array.isArray(value) ? `${value.length} akses` : "Belum ada akses"}</span>);

function SettingsFormShell({ props }: { props: CustomFormViewProps }) {
  const { schema, basePath, id, values, editing, saving, onEdit, onChange, onSave } = props;
  const Icon = UserRound;
  const title = String(values.name || "Pengguna baru");
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field]));
  const field = (name: string) => { const meta = fields[name]; if (!meta) return null; return <label><span>{meta.label}</span><div>{editing ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>; };
  return <div className="luma-settings-record"><header><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft/></Link></Button><div className="luma-settings-record-icon"><Icon/></div><div><h1>{title}</h1><p>{String(values.email || values.login || "Email belum diisi")}</p></div><div>{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header><main>{schema.form.sections.map((section) => <section key={section.id || section.label}><h2>{section.label}</h2>{section.description && <p>{section.description}</p>}<div className="luma-settings-record-grid">{section.fields.map((meta) => field(meta.name))}</div></section>)}</main></div>;
}

export function UserSettingsForm(props: CustomFormViewProps) { return <SettingsFormShell props={props}/>; }
