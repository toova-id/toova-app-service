import { ArrowLeft, Layers3, Save } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@luma/components/ui/button";
import { FieldEditor, FieldValue } from "@luma/views/field-registry";
import type { CustomFormViewProps } from "@luma/views/view-registry";
import type { FieldSchema } from "@luma/views/types";

export default function AttributeForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const field = (name: string, className = "") => { const meta = fields[name]; if (!meta) return null; return <label className={`luma-customer-field ${className}`}><span>{meta.label}{meta.required && <b>*</b>}</span><div>{editing && !meta.readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>; };
  const valueCount = Array.isArray(values.value_ids) ? values.value_ids.filter((row) => typeof row !== "object" || row === null || !("active" in row) || row.active !== false).length : 0;
  const mode = fields.create_variant?.selection?.find(([key]) => key === values.create_variant)?.[1] || "Belum dipilih";
  return <div className="luma-customer luma-attribute-page">
    <header className="luma-customer-header"><div className="luma-customer-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div className="luma-customer-avatar"><Layers3/></div><div><span>Atribut produk</span><h1>{id ? String(values.name || "Atribut") : "Atribut baru"}</h1><p>{valueCount} nilai · {mode}</p></div></div><div className="luma-customer-actions">{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header>
    <main className="luma-customer-body"><section className="luma-customer-section"><header><h2>Konfigurasi atribut</h2><p>Tentukan nama, tampilan pilihan, dan kapan Odoo membuat variants.</p></header><div className="luma-customer-grid">{field("name")}{field("display_type")}{field("create_variant")}</div></section><section className="luma-customer-section"><header><h2>Nilai atribut</h2><p>Nilai ini dipilih pada Product. Contoh: Hitam, Putih atau S, M, L.</p></header><div className="luma-customer-relation">{field("value_ids")}</div></section>{id && <section className="luma-customer-section"><header><h2>Penggunaan</h2><p>Jumlah product template yang menggunakan atribut ini.</p></header><div className="luma-customer-grid">{field("number_related_products")}</div></section>}</main>
  </div>;
}
