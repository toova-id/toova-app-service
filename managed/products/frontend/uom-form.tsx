import { ArrowLeft, Ruler, Save } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@toova/components/ui/button";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";
import { UomUnitsEditor, UomUnitsValue } from "./uom-units";

export default function UomForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const name = fields.name;
  const units = Array.isArray(values.uom_ids) ? values.uom_ids as Record<string, unknown>[] : [];
  const active = units.filter((row) => row.active !== false);
  const base = active.find((row) => row.uom_type === "reference");
  const nameField = name ? <label className="toova-customer-field"><span>{name.label}{name.required && <b>*</b>}</span><div>{editing ? <FieldEditor actionId={schema.id} field={name} value={values.name} parentValues={values} onChange={(value) => onChange("name", value)}/> : <FieldValue field={name} value={values.name} record={values}/>}</div></label> : null;
  return <div className="toova-customer toova-uom-page">
    <header className="toova-customer-header"><div className="toova-customer-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div className="toova-customer-avatar"><Ruler/></div><div><span>Kelompok satuan</span><h1>{id ? String(values.name || "Satuan") : "Kelompok satuan baru"}</h1><p>{active.length} satuan{base ? ` · dasar ${String(base.name)}` : " · satuan dasar belum dibuat"}</p></div></div><div className="toova-customer-actions">{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan satuan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header>
    <main className="toova-customer-body">
      <section className="toova-customer-section"><header><h2>Kelompok satuan</h2><p>Satuan dalam kelompok sama dapat dikonversi, misalnya L dan ml atau kg dan g.</p></header><div className="toova-attribute-name">{nameField}</div></section>
      <section className="toova-customer-section"><header><h2>Satuan & konversi</h2><p>Tentukan satuan dasar, lalu masukkan nilai setiap satuan sebagai jumlah satuan dasar.</p></header><div className="toova-customer-relation">{editing && fields.uom_ids ? <UomUnitsEditor field={fields.uom_ids} value={values.uom_ids} onChange={(value) => onChange("uom_ids", value)}/> : fields.uom_ids ? <UomUnitsValue value={values.uom_ids}/> : null}</div><aside className="toova-attribute-unit-note"><Ruler/><div><strong>Ukuran kemasan bukan satuan transaksi</strong><span>Produk botol 250 ml dan 500 ml memakai UoM unit dengan atribut Isi kemasan. Gunakan L/ml untuk produk cair curah yang stoknya dikonversi.</span></div></aside></section>
    </main>
  </div>;
}
