import { ArrowLeft, Check, Save } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@toova/components/ui/button";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import { modifierActive } from "@toova/views/modifiers";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

export default function SaleOrderForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave, onButton }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || schema.form.sections.flatMap((section) => section.fields)).map((field) => [field.name, field]));
  const quotation = schema.actionXmlid === "sales.action_quotations";
  const status = schema.form.statusField;
  const statusOptions = status?.selection?.filter(([key]) => !schema.form.statusVisible.length || schema.form.statusVisible.includes(key)) ?? [];
  const statusIndex = status ? statusOptions.findIndex(([key]) => key === values[status.name]) : -1;
  const statusLabel = status?.selection?.find(([key]) => key === values[status.name])?.[1];
  const visibleButtons = schema.form.buttons.filter((button) => !modifierActive(button.modifiers, "invisible", values));
  const moneyField = (name: string) => fields[name] ? <FieldValue field={fields[name]} value={values[name]} record={values}/> : <>—</>;
  const field = (name: string, className = "") => {
    const meta = fields[name] as FieldSchema | undefined;
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const readonly = Boolean(meta.readonly) || modifierActive(meta.modifiers, "readonly", values);
    const required = Boolean(meta.required) || modifierActive(meta.modifiers, "required", values);
    return <label className={`toova-document-field ${className}`} title={meta.help}><span>{meta.label}{required && <b>*</b>}</span><div>{editing && !readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>;
  };
  const advanced = ["pricelist_id", "payment_term_id", "fiscal_position_id", "warehouse_id", "picking_policy", "incoterm", "incoterm_location", "commitment_date", "user_id", "team_id", "company_id"];

  return <div className="toova-document">
    <header className="toova-document-header"><div className="toova-document-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div><h1>{id ? String(values.name || values.display_name || schema.form.title) : "Penawaran baru"}</h1>{id && statusLabel && <span>{statusLabel}</span>}</div></div><div className="toova-document-actions">{id && visibleButtons.map((button) => <Button key={`${button.type}:${button.name}:${button.label}`} variant={button.primary ? "default" : "outline"} onClick={() => onButton(button.name, button.type)}>{button.label}</Button>)}{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : quotation ? "Simpan penawaran" : "Simpan pesanan"}</Button> : schema.form.write && <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header>
    {id && status && statusIndex >= 0 && <nav className="toova-document-workflow" aria-label="Progres dokumen"><ol>{statusOptions.map(([key, label], index) => <li key={key} className={index < statusIndex ? "completed" : index === statusIndex ? "current" : undefined} aria-current={index === statusIndex ? "step" : undefined}><i>{index < statusIndex ? <Check/> : index + 1}</i><span>{label}</span></li>)}</ol></nav>}
    <main className="toova-document-body">
      <section className="toova-document-overview"><h2>Pelanggan</h2><div className="toova-document-overview-grid"><div className="toova-document-primary">{field("partner_id", "toova-document-hero")}<div className="toova-document-addresses">{field("partner_invoice_id")}{field("partner_shipping_id")}</div></div><div className="toova-document-meta">{field("date_order", "toova-document-meta-wide")}{quotation && field("validity_date")}{field("client_order_ref")}</div></div></section>
      <section className="toova-document-section toova-document-lines"><header><h2>Produk dan layanan</h2><span>Pilih variant. Harga, pajak, dan satuan dihitung Odoo.</span></header>{field("order_line", "toova-document-table")}</section>
      <section className="toova-document-summary"><div>{field("note", "toova-document-note")}</div><dl><div><dt>Subtotal</dt><dd>{moneyField("amount_untaxed")}</dd></div><div><dt>Pajak</dt><dd>{moneyField("amount_tax")}</dd></div><div className="total"><dt>Total</dt><dd>{moneyField("amount_total")}</dd></div></dl></section>
      <details className="toova-document-advanced"><summary>Pengaturan lanjutan</summary><div>{advanced.map((name) => field(name)).filter(Boolean)}</div></details>
      {!quotation && <section className="toova-document-section toova-document-progress"><header><h2>Status proses</h2><span>Pengiriman dikerjakan di Persediaan. Invoice dan pembayaran dikerjakan di Keuangan.</span></header><div>{field("delivery_status")}{field("invoice_status")}</div></section>}
    </main>
  </div>;
}
