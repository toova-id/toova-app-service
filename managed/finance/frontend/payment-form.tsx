import { ArrowDownLeft, ArrowUpRight, CheckCircle2, Landmark, ReceiptText } from "lucide-react";
import { DocumentRelations } from "@toova/components/document-relations";
import { ManagedFormShell } from "@toova/components/managed-form";
import { Button } from "@toova/components/ui/button";
import { FieldValue } from "@toova/views/field-registry";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

export default function PaymentForm({ schema, id, values, relatedDocuments, onBack }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const inbound = values.payment_type === "inbound";
  const posted = values.state === "posted";
  const field = (name: string) => fields[name] ? <div className="toova-payment-detail"><span>{fields[name].label}</span><b><FieldValue field={fields[name]} value={values[name]} record={values}/></b></div> : null;
  const amount = fields.amount ? <FieldValue field={fields.amount} value={values.amount} record={values}/> : <>—</>;
  const stateLabel = fields.state?.selection?.find(([key]) => key === values.state)?.[1] || String(values.state || "Draf");
  const documentNumber = values.name && values.name !== "/" ? String(values.name) : "Belum bernomor";

  return <ManagedFormShell icon={inbound ? <ArrowDownLeft/> : <ArrowUpRight/>} title={id ? documentNumber : "Pembayaran"} subtitle={String(values.payment_reference || "Tanpa referensi")} actions={<DocumentRelations groups={relatedDocuments}/>} onBack={onBack} className={`toova-payment-document ${inbound ? "inbound" : "outbound"}`}>
    <div className="toova-payment-body"><section className="toova-payment-hero"><div className={`toova-payment-direction ${inbound ? "inbound" : "outbound"}`}>{inbound ? <ArrowDownLeft/> : <ArrowUpRight/>}</div><span>{inbound ? "Diterima dari" : "Dibayarkan kepada"}</span><h2>{Array.isArray(values.partner_id) ? String(values.partner_id[1]) : "Mitra belum ditentukan"}</h2><strong>{amount}</strong><p>{values.date ? new Date(`${values.date}T00:00:00`).toLocaleDateString("id-ID", { dateStyle: "long" }) : "Tanggal belum ditentukan"}</p><i className={posted ? "done" : "draft"}>{posted ? <CheckCircle2/> : <ReceiptText/>}{stateLabel}</i></section>

      <section className="toova-payment-info"><header><Landmark/><div><h2>Detail pembayaran</h2><p>Data ini berasal dari jurnal dan rekonsiliasi native Odoo.</p></div></header><div>{field("journal_id")}{field("payment_method_line_id")}{field("partner_type")}{field("currency_id")}{field("payment_reference")}{field("is_reconciled")}</div></section></div>
  </ManagedFormShell>;
}
