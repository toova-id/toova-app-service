import { ArrowLeft, Save } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@luma/components/ui/button";
import { FieldEditor, FieldValue } from "@luma/views/field-registry";
import { modifierActive } from "@luma/views/modifiers";
import type { CustomFormViewProps } from "@luma/views/view-registry";
import type { FieldSchema } from "@luma/views/types";

export default function SaleOrderForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave, onButton }: CustomFormViewProps) {
  const fields = Object.fromEntries(schema.form.sections.flatMap((section) => section.fields).map((field) => [field.name, field]));
  const status = schema.form.statusField;
  const statusOptions = status?.selection?.filter(([key]) => !schema.form.statusVisible.length || schema.form.statusVisible.includes(key)) ?? [];
  const visibleButtons = schema.form.buttons.filter((button) => !modifierActive(button.modifiers, "invisible", values));

  const moneyField = (name: string) => fields[name] ? <FieldValue field={fields[name]} value={values[name]} record={values}/> : <>—</>;
  const field = (name: string, className = "") => {
    const meta = fields[name] as FieldSchema | undefined;
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const readonly = Boolean(meta.readonly) || modifierActive(meta.modifiers, "readonly", values);
    const required = Boolean(meta.required) || modifierActive(meta.modifiers, "required", values);
    return <label className={`luma-document-field ${className}`} title={meta.help}>
      <span>{meta.label}{required && <b>*</b>}</span>
      <div>{editing && !readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div>
    </label>;
  };

  return <div className="luma-document">
    <header className="luma-document-header">
      <div className="luma-document-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div><h1>{id ? String(values.name || values.display_name || schema.form.title) : "Penawaran baru"}</h1></div></div>
      <div className="luma-document-actions">{id && visibleButtons.map((button) => <Button key={`${button.type}:${button.name}:${button.label}`} variant={button.primary ? "default" : "outline"} onClick={() => onButton(button.name, button.type)}>{button.label}</Button>)}{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div>
    </header>

    {status && <div className="luma-document-status"><ol>{statusOptions.map(([key, label]) => <li key={key} className={values[status.name] === key ? "active" : undefined}><i/>{label}</li>)}</ol></div>}

    <main className="luma-document-body">
      <section className="luma-document-overview">
        <div className="luma-document-primary"><span className="luma-document-eyebrow">Pelanggan</span>{field("partner_id", "luma-document-hero")}{field("partner_invoice_id")}{field("partner_shipping_id")}</div>
        <div className="luma-document-meta">{field("date_order")}{field("validity_date")}{field("commitment_date")}{field("client_order_ref")}{field("user_id")}{field("team_id")}</div>
      </section>

      <section className="luma-document-section"><header><h2>Detail komersial</h2><span>Harga, pembayaran, dan pemenuhan</span></header><div className="luma-document-fields">{field("pricelist_id")}{field("payment_term_id")}{field("fiscal_position_id")}{field("warehouse_id")}{field("picking_policy")}{field("incoterm")}</div></section>

      <section className="luma-document-section luma-document-lines"><header><h2>Item pesanan</h2><span>Produk, kuantitas, harga, dan pajak</span></header>{field("order_line", "luma-document-table")}</section>

      <section className="luma-document-summary"><div>{field("note", "luma-document-note")}</div><dl><div><dt>Subtotal</dt><dd>{moneyField("amount_untaxed")}</dd></div><div><dt>Pajak</dt><dd>{moneyField("amount_tax")}</dd></div><div className="total"><dt>Total</dt><dd>{moneyField("amount_total")}</dd></div></dl></section>
    </main>
  </div>;
}
