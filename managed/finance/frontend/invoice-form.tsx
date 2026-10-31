import { CalendarDays, CircleDollarSign, FileCheck2, ReceiptText, Save, UserRound } from "lucide-react";
import { DocumentBack, DocumentRelations } from "@toova/components/document-relations";
import { Button } from "@toova/components/ui/button";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import { modifierActive } from "@toova/views/modifiers";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

type Row = Record<string, unknown>;

export default function InvoiceForm({ schema, id, values, relatedDocuments, editing, saving, onEdit, onChange, onSave, onButton, onBack }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const lines = Array.isArray(values.invoice_line_ids) ? values.invoice_line_ids as Row[] : [];
  const draft = values.state === "draft";
  const creditNote = values.move_type === "out_refund";
  const visibleButtons = schema.form.buttons.filter((button) => !modifierActive(button.modifiers, "invisible", values));
  const stateLabel = fields.state?.selection?.find(([key]) => key === values.state)?.[1] || String(values.state || "Draf");
  const paymentLabel = fields.payment_state?.selection?.find(([key]) => key === values.payment_state)?.[1] || "Belum dibayar";
  const paymentTone = values.payment_state === "paid" ? "done" : values.payment_state === "partial" || values.payment_state === "in_payment" ? "work" : values.payment_state === "reversed" ? "warn" : "idle";
  const documentNumber = values.name && values.name !== "/" ? String(values.name) : "Belum bernomor";
  const field = (name: string, className = "") => {
    const meta = fields[name];
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const writable = editing && draft && !meta.readonly;
    return <label className={`toova-finance-field ${className}`}><span>{meta.label}{meta.required && <b>*</b>}</span><div>{writable ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>;
  };
  const money = (name: string) => fields[name] ? <FieldValue field={fields[name]} value={values[name]} record={values}/> : <>—</>;
  const lineValue = (row: Row, name: string) => fields.invoice_line_ids?.relationView?.columns.find((column) => column.name === name);
  const renderLine = (row: Row, name: string) => {
    const meta = lineValue(row, name);
    return meta ? <FieldValue field={meta} value={row[name]} record={{ ...row, currency_id: values.currency_id }}/> : <>—</>;
  };

  return <div className="toova-finance-document">
    <header className="toova-finance-header"><div className="toova-finance-title"><DocumentBack onBack={onBack}/><div className="toova-finance-mark"><ReceiptText/></div><div><h1>{id ? documentNumber : "Faktur baru"}</h1><p>{String(values.invoice_origin || "Tanpa pesanan sumber")}</p></div></div><div className="toova-finance-actions"><DocumentRelations groups={relatedDocuments}/>{id && visibleButtons.map((button) => <Button key={`${button.type}:${button.name}`} variant={button.primary ? "default" : "outline"} onClick={() => onButton(button.name, button.type)}>{button.label}</Button>)}{draft && schema.form.write && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan draf"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header>

    <div className="toova-finance-status"><span data-tone={values.state === "posted" ? "done" : values.state === "cancel" ? "warn" : "work"}><FileCheck2/><i>Status dokumen</i><b>{stateLabel}</b></span><span data-tone={paymentTone}><CircleDollarSign/><i>Pembayaran</i><b>{paymentLabel}</b></span><span><CalendarDays/><i>Jatuh tempo</i><b>{values.invoice_date_due ? new Date(`${values.invoice_date_due}T00:00:00`).toLocaleDateString("id-ID", { dateStyle: "medium" }) : "Belum ditentukan"}</b></span></div>

    <main className="toova-finance-body">
      <section className="toova-finance-overview"><div className="toova-finance-customer"><UserRound/><div><span>Pelanggan</span>{field("partner_id", "hero")}</div></div><div className="toova-finance-meta">{field("invoice_date")}{field("invoice_date_due")}{field("invoice_payment_term_id")}{field("currency_id")}{field("ref")}{field("invoice_origin")}</div></section>

      <section className="toova-finance-lines"><header><div><h2>Rincian tagihan</h2><p>Nilai berasal dari Sales Order dan perhitungan pajak native Odoo.</p></div><b>{lines.length} baris</b></header><div className="overflow-x-auto"><table><thead><tr><th>Produk / Variant</th><th>Deskripsi</th><th className="number">Kuantitas</th><th>Satuan</th><th className="number">Harga</th><th>Pajak</th><th className="number">Subtotal</th></tr></thead><tbody>{lines.map((row, index) => <tr key={String(row.id || index)}><td>{renderLine(row, "product_id")}</td><td>{renderLine(row, "name")}</td><td className="number">{renderLine(row, "quantity")}</td><td>{renderLine(row, "product_uom_id")}</td><td className="number">{renderLine(row, "price_unit")}</td><td>{renderLine(row, "tax_ids")}</td><td className="number">{renderLine(row, "price_subtotal")}</td></tr>)}</tbody></table>{!lines.length && <div className="toova-finance-empty">Belum ada baris invoice.</div>}</div></section>

      <section className="toova-finance-closing"><div>{field("narration", "note")}</div><aside><dl><div><dt>Subtotal</dt><dd>{money("amount_untaxed")}</dd></div><div><dt>Pajak</dt><dd>{money("amount_tax")}</dd></div><div className="total"><dt>Total</dt><dd>{money("amount_total")}</dd></div><div className="residual"><dt>Sisa tagihan</dt><dd>{money("amount_residual")}</dd></div></dl><p data-tone={paymentTone}>{paymentLabel}</p></aside></section>
    </main>
  </div>;
}
