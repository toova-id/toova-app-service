import { ArrowLeft, BadgeDollarSign, Save } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@luma/components/ui/button";
import { FieldEditor, FieldValue } from "@luma/views/field-registry";
import type { CustomFormViewProps } from "@luma/views/view-registry";
import type { FieldSchema } from "@luma/views/types";
import { PricelistRulesEditor, PricelistRulesValue } from "./pricelist-rules";

export default function PricelistForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave }: CustomFormViewProps) {
  const [advanced, setAdvanced] = useState(false);
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const field = (name: string) => { const meta = fields[name]; if (!meta) return null; return <label className="luma-customer-field" title={meta.help}><span>{meta.label}{meta.required && <b>*</b>}</span><div>{editing && !meta.readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>; };
  const rules = Array.isArray(values.item_ids) ? values.item_ids.filter((row) => typeof row !== "object" || row === null || !("active" in row) || row.active !== false).length : 0;
  const currency = Array.isArray(values.currency_id) ? values.currency_id[1] : "Mata uang belum dipilih";
  return <div className="luma-customer luma-pricelist-page">
    <header className="luma-customer-header"><div className="luma-customer-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div className="luma-customer-avatar"><BadgeDollarSign/></div><div><span>Daftar harga</span><h1>{id ? String(values.name || "Daftar harga") : "Daftar harga baru"}</h1><p>{currency} · {rules} aturan · {values.active === false ? "Diarsipkan" : "Aktif"}</p></div></div><div className="luma-customer-actions">{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan daftar harga"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header>
    <main className="luma-customer-body">
      <section className="luma-customer-section"><header><h2>Identitas daftar harga</h2><p>Daftar harga dipilih pada customer atau transaksi penjualan.</p></header><div className="luma-customer-grid">{field("name")}{field("currency_id")}{field("company_id")}{field("active")}</div></section>
      <section className="luma-customer-section"><header><h2>Aturan harga</h2><p>Aturan paling spesifik dan minimum kuantitas terbesar diprioritaskan oleh engine Odoo.</p></header><div className="luma-customer-relation">{editing && fields.item_ids ? <PricelistRulesEditor actionId={schema.id} field={fields.item_ids} value={values.item_ids} parentValues={values} onChange={(value) => onChange("item_ids", value)}/> : fields.item_ids ? <PricelistRulesValue value={values.item_ids}/> : null}</div></section>
      <section className="luma-customer-section luma-attribute-advanced-section"><div className="luma-attribute-advanced"><button type="button" aria-expanded={advanced} onClick={() => setAdvanced((value) => !value)}><div><strong>Pengaturan lanjutan</strong><span>Atur tampilan diskon dan pembatasan wilayah.</span></div><span>{advanced ? "−" : "+"}</span></button>{advanced && <div className="luma-customer-grid">{field("discount_policy")}{field("country_group_ids")}</div>}</div></section>
    </main>
  </div>;
}
