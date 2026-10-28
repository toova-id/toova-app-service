import { Building2, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api, apiMutation } from "@luma/lib/api";
import { Button } from "@luma/components/ui/button";
import { Combobox } from "@luma/components/ui/combobox";
import { FieldEditor, FieldValue } from "@luma/views/field-registry";
import type { FieldSchema } from "@luma/views/types";
import type { SettingsSectionProps } from "@luma/features/settings/settings-registry";

const fields: FieldSchema[] = [
  { name: "logo", label: "Logo", type: "binary", widget: "image" }, { name: "name", label: "Nama legal", type: "char", required: true },
  { name: "email", label: "Email", type: "char", widget: "email" }, { name: "phone", label: "Telepon", type: "char", widget: "phone" }, { name: "website", label: "Website", type: "char", widget: "url" },
  { name: "street", label: "Alamat", type: "char" }, { name: "street2", label: "Alamat lanjutan", type: "char" }, { name: "city", label: "Kota", type: "char" },
  { name: "state_id", label: "Provinsi", type: "many2one", relation: "res.country.state" }, { name: "zip", label: "Kode pos", type: "char" }, { name: "country_id", label: "Negara", type: "many2one", relation: "res.country" },
  { name: "currency_id", label: "Mata uang utama", type: "many2one", relation: "res.currency", readonly: true }, { name: "vat", label: "NPWP / TIN", type: "char" },
  { name: "l10n_id_pkp", label: "PKP", type: "boolean" }, { name: "l10n_id_tku", label: "TKU / NITKU", type: "char" }, { name: "l10n_id_tax_name", label: "Nama legal pajak", type: "char" }, { name: "l10n_id_tax_address", label: "Alamat pajak", type: "text" },
];
const sections = [
  ["Identitas", "", ["logo", "name", "email", "phone", "website"]],
  ["Alamat", "", ["street", "street2", "country_id", "state_id", "city", "zip"]],
  ["Pajak & mata uang", "", ["currency_id", "vat", "l10n_id_pkp", "l10n_id_tku", "l10n_id_tax_name", "l10n_id_tax_address"]],
] as const;

export default function GeneralSettings({ section }: SettingsSectionProps) {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();
  const [relations, setRelations] = useState<Record<string, { id: number; label: string }[]>>({});
  useEffect(() => { api<{ values: Record<string, unknown> }>("/api/v1/settings/general").then((result) => setValues(result.values)).catch((reason) => setError(reason.message)); }, []);
  const save = async () => { setSaving(true); setError(undefined); try { const payload = Object.fromEntries(fields.filter((field) => !field.readonly).map((field) => [field.name, values[field.name]])); const result = await apiMutation<{ values: Record<string, unknown> }>("/api/v1/settings/general", "POST", { values: payload }); setValues(result.values); setEditing(false); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } finally { setSaving(false); } };
  const loadRelation = async (field: FieldSchema, query = "") => { const country = Array.isArray(values.country_id) ? values.country_id[0] : values.country_id; const params = new URLSearchParams({ q: query, ...(field.name === "state_id" && country ? { countryId: String(country) } : {}) }); const result = await api<{ items: { id: number; label: string }[] }>(`/api/v1/settings/relations/${field.relation}?${params}`); setRelations((current) => ({ ...current, [field.name]: result.items })); };
  const render = (name: string) => { const field = fields.find((item) => item.name === name)!; const current = values[name]; const relationValue = Array.isArray(current) ? { value: Number(current[0]), label: String(current[1]) } : undefined; return <label key={name}><span>{field.label}{field.required && <b>*</b>}</span><div>{editing && !field.readonly ? field.type === "many2one" ? <Combobox options={(relations[name] || []).map((item) => ({ value: item.id, label: item.label }))} value={relationValue} onSearch={(query) => loadRelation(field, query)} onChange={(option) => setValues((state) => ({ ...state, [name]: option ? [option.value, option.label] : false }))} placeholder="Pilih..."/> : <FieldEditor actionId={0} field={field} value={current} parentValues={values} onChange={(value) => setValues((state) => ({ ...state, [name]: value }))}/> : <FieldValue field={field} value={current} record={values}/>}</div></label>; };
  return <div className="luma-settings-provider"><div className="luma-settings-profile"><div className="luma-settings-profile-mark"><Building2/></div><div><h2>{String(values.name || "Perusahaan")}</h2><p>{String(values.email || values.phone || "Kontak belum lengkap")}</p></div>{section.level === "write" && (editing ? <Button onClick={save} disabled={saving}><Save/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={() => setEditing(true)}>Edit informasi</Button>)}</div>{error && <div className="workspace-toast-error">{error}</div>}{sections.map(([title, description, names]) => <section key={title}><header><h2>{title}</h2>{description && <p>{description}</p>}</header><div className="luma-settings-record-grid">{names.map(render)}</div></section>)}</div>;
}
