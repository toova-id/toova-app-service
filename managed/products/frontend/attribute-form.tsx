import { Box, ChevronDown, Layers3, Save } from "lucide-react";
import { useState } from "react";
import { Button } from "@toova/components/ui/button";
import { ManagedFormShell } from "@toova/components/managed-form";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";
import { AttributeValuesEditor, AttributeValuesValue } from "./attribute-values";

export default function AttributeForm({ schema, id, values, editing, saving, onEdit, onChange, onSave, onBack }: CustomFormViewProps) {
  const [advanced, setAdvanced] = useState(false);
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const field = (name: string, className = "", forceReadonly = false) => { const meta = fields[name]; if (!meta) return null; return <label className={`managed-form-field ${className}`} title={meta.help}><span>{meta.label}{meta.required && <b>*</b>}</span><div>{editing && !meta.readonly && !forceReadonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>; };
  const rows = Array.isArray(values.value_ids) ? values.value_ids as Record<string, unknown>[] : [];
  const valueCount = rows.filter((row) => row.active !== false).length;
  const mode = fields.create_variant?.selection?.find(([key]) => key === values.create_variant)?.[1] || "Belum dipilih";
  const usedByProducts = Number(values.number_related_products || 0);
  return <ManagedFormShell icon={<Layers3/>} title={id ? String(values.name || "Atribut") : "Atribut baru"} subtitle={`${valueCount} pilihan · ${mode}`} actions={(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan atribut"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)} onBack={onBack} className="toova-customer toova-attribute-page">
      <section className="managed-form-section"><header><h2>Nama atribut</h2><p>Gunakan kategori pembeda produk, misalnya Warna, Ukuran, atau Isi kemasan.</p></header><div className="toova-attribute-name">{field("name")}</div></section>
      <section className="managed-form-section"><header><h2>Pilihan nilai</h2><p>Masukkan nilai yang dipilih pada produk. Satuan boleh menjadi bagian nama, misalnya 250 ml, 500 ml, dan 1 L.</p></header><div className="managed-form-relation">{editing && fields.value_ids ? <AttributeValuesEditor actionId={schema.id} field={fields.value_ids} value={values.value_ids} parentValues={values} advanced={advanced} onChange={(value) => onChange("value_ids", value)}/> : fields.value_ids ? <AttributeValuesValue value={values.value_ids}/> : null}</div><aside className="toova-attribute-unit-note"><Box/><div><strong>Ukuran kemasan didukung</strong><span>Untuk botol 250 ml dan 500 ml, buat atribut “Isi kemasan”. Setiap pilihan menjadi variant dan stoknya terpisah. Untuk barang cair curah, gunakan UoM ml/L, bukan variant.</span></div></aside></section>
      <section className="managed-form-section toova-attribute-advanced-section"><div className="toova-attribute-advanced"><button type="button" aria-expanded={advanced} onClick={() => setAdvanced((value) => !value)}><div><strong>Pengaturan lanjutan</strong><span>Ubah tampilan pilihan dan waktu pembuatan varian.</span></div><ChevronDown className={advanced ? "open" : undefined}/></button>{advanced && <div className="managed-form-grid">{field("display_type")}{field("create_variant", "", usedByProducts > 0)}{usedByProducts > 0 && <p className="toova-attribute-mode-lock">Cara varian dibuat terkunci karena atribut sudah digunakan produk.</p>}</div>}</div></section>
      {id && <section className="managed-form-section"><header><h2>Penggunaan</h2><p>Mode pembuatan varian tidak dapat diubah setelah atribut dipakai produk.</p></header><div className="toova-attribute-usage">{field("number_related_products")}</div></section>}
  </ManagedFormShell>;
}
