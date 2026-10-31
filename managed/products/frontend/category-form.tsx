import { FolderTree, Save } from "lucide-react";
import { Button } from "@toova/components/ui/button";
import { ManagedFormShell } from "@toova/components/managed-form";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

export default function CategoryForm({ schema, id, values, editing, saving, onEdit, onChange, onSave, onBack }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const field = (name: string) => { const meta = fields[name]; if (!meta) return null; return <label className="toova-customer-field" title={meta.help}><span>{meta.label}{meta.required && <b>*</b>}</span><div>{editing && !meta.readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>; };
  const accounting = fields.property_account_income_categ_id || fields.property_account_expense_categ_id;
  return <ManagedFormShell icon={<FolderTree/>} title={id ? String(values.name || "Kategori") : "Kategori baru"} subtitle={String(values.complete_name || "Atur pengelompokan katalog produk")} actions={(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan kategori"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)} onBack={onBack} className="toova-customer toova-category-page">
      <section className="toova-customer-section"><header><h2>Identitas kategori</h2><p>Gunakan kategori untuk pencarian produk, aturan harga, dan default accounting.</p></header><div className="toova-customer-grid">{field("name")}{field("parent_id")}</div></section>
      {id && <section className="toova-customer-section"><header><h2>Penggunaan</h2><p>Jumlah mencakup produk pada kategori ini dan seluruh turunannya.</p></header><div className="toova-category-summary">{field("complete_name")}{field("product_count")}</div></section>}
      {accounting && <section className="toova-customer-section"><header><h2>Default accounting</h2><p>Produk tanpa akun khusus mewarisi akun dari kategori ini.</p></header><div className="toova-customer-grid">{field("property_account_income_categ_id")}{field("property_account_expense_categ_id")}</div></section>}
  </ManagedFormShell>;
}
