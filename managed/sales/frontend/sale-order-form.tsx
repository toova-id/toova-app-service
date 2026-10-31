import { ArrowUpRight, CalendarDays, Check, CircleDollarSign, FileText, PackageCheck, Save, ShoppingCart, UserRound } from "lucide-react";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { DocumentBack, DocumentRelations } from "@toova/components/document-relations";
import { findByActionXmlid, useNavigation } from "@toova/app/navigation";
import { Button } from "@toova/components/ui/button";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import { modifierActive } from "@toova/views/modifiers";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

type Tab = "summary" | "items" | "delivery" | "invoice" | "settings";

export default function SaleOrderForm({ schema, id, values, relatedDocuments, editing, saving, onEdit, onChange, onSave, onButton, onBack }: CustomFormViewProps) {
  const [tab, setTab] = useState<Tab>("summary");
  const location = useLocation();
  const navigate = useNavigate();
  const navigation = useNavigation();
  const fields = Object.fromEntries((schema.form.allFields || schema.form.sections.flatMap((section) => section.fields)).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const quotation = schema.actionXmlid === "sales.action_quotations";
  const status = schema.form.statusField;
  const statusOptions = status?.selection?.filter(([key]) => !schema.form.statusVisible.length || schema.form.statusVisible.includes(key)) ?? [];
  const statusIndex = status ? statusOptions.findIndex(([key]) => key === values[status.name]) : -1;
  const visibleButtons = schema.form.buttons.filter((button) => !modifierActive(button.modifiers, "invisible", values));
  const primaryButton = visibleButtons.find((button) => button.primary);
  const secondaryButtons = visibleButtons.filter((button) => button !== primaryButton);
  const itemCount = Array.isArray(values.order_line) ? values.order_line.filter((row) => typeof row !== "object" || row === null || !("display_type" in row) || !row.display_type).length : 0;
  const relationCount = (name: string) => Array.isArray(values[name]) ? values[name].length : 0;
  const deliveryCount = relationCount("picking_ids");
  const invoiceCount = relationCount("invoice_ids");
  const deliveryState = String(values.delivery_status || "pending");
  const invoiceState = String(values.invoice_status || "no");
  const customer = Array.isArray(values.partner_id) ? String(values.partner_id[1]) : "Pelanggan belum dipilih";
  const related = (key: string) => relatedDocuments.find((group) => group.key === key);
  const openRelated = (actionXmlid: string, recordId: number) => {
    const path = findByActionXmlid(navigation, actionXmlid)?.path;
    if (!path) return;
    const trail = Array.isArray(location.state?.managedTrail) ? location.state.managedTrail : [];
    navigate(`${path}/${recordId}`, { state: { managedTrail: [`${location.pathname}${location.search}`, ...trail] } });
  };

  const field = (name: string, className = "") => {
    const meta = fields[name];
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const readonly = Boolean(meta.readonly) || modifierActive(meta.modifiers, "readonly", values);
    const required = Boolean(meta.required) || modifierActive(meta.modifiers, "required", values);
    return <label className={`toova-sales-field ${className}`} title={meta.help}><span>{meta.label}{required && <b>*</b>}</span><div>{editing && !readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>;
  };
  const money = (name: string) => fields[name] ? <FieldValue field={fields[name]} value={values[name]} record={values}/> : <>—</>;
  const selection = (name: string) => fields[name]?.selection?.find(([key]) => key === values[name])?.[1] || "Belum diproses";
  const section = (title: string, description: string, content: JSX.Element) => <section className="toova-sales-section"><header><h2>{title}</h2><p>{description}</p></header>{content}</section>;
  const tabs: [Tab, string, number?][] = quotation
    ? [["summary", "Ringkasan"], ["items", "Item", itemCount], ["settings", "Pengaturan"]]
    : [["summary", "Ringkasan"], ["items", "Item", itemCount], ["delivery", "Pengiriman", deliveryCount], ["invoice", "Faktur", invoiceCount], ["settings", "Pengaturan"]];

  return <div className="toova-sales-document">
    <header className="toova-sales-header">
      <div className="toova-sales-title"><DocumentBack onBack={onBack}/><div className="toova-sales-mark"><ShoppingCart/></div><div><div className="toova-sales-heading"><h1>{id ? String(values.name || "Pesanan") : "Penawaran baru"}</h1>{id && status && <div className="toova-sales-state"><button type="button" aria-label={`Status saat ini: ${selection("state")}`}>{selection("state")}</button><div role="tooltip"><span>Perjalanan dokumen</span><ol>{statusOptions.map(([key, label], index) => <li key={key} className={index < statusIndex ? "completed" : index === statusIndex ? "current" : undefined}><i>{index < statusIndex ? <Check/> : index + 1}</i><b>{label}</b></li>)}</ol></div></div>}</div><p>{customer}</p></div></div>
      <div className="toova-sales-actions"><DocumentRelations groups={relatedDocuments}/>{id && secondaryButtons.map((button) => <Button key={`${button.type}:${button.name}`} variant="outline" onClick={() => onButton(button.name, button.type)}>{button.label}</Button>)}{id && primaryButton && <Button onClick={() => onButton(primaryButton.name, primaryButton.type)}>{primaryButton.label}</Button>}{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : schema.form.write && <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div>
    </header>

    <nav className="toova-sales-tabs" aria-label="Bagian penjualan">{tabs.map(([key, label, count]) => <button key={key} type="button" className={tab === key ? "active" : undefined} onClick={() => setTab(key)}>{label}{count !== undefined && <i>{count}</i>}</button>)}</nav>

    <main className="toova-sales-body">
      {tab === "summary" && <>
        {section("Pelanggan", "Identitas, alamat, dan referensi transaksi.", <div className="toova-sales-overview"><div className="toova-sales-customer"><UserRound/><div><span>Pelanggan</span><h3>{customer}</h3></div></div><div className="toova-sales-grid">{field("partner_id")}{field("client_order_ref")}{field("partner_invoice_id")}{field("partner_shipping_id")}{field("date_order")}{quotation && field("validity_date")}</div></div>)}
        {!quotation && section("Progres pesanan", "Pantau pemenuhan dan penagihan tanpa meninggalkan pesanan.", <div className="toova-sales-process"><div className="toova-sales-process-lanes"><article data-tone={deliveryState === "full" ? "done" : deliveryState === "pending" ? "idle" : "work"}><div className="toova-sales-process-icon"><PackageCheck/></div><div><span>Pengiriman</span><h3>{selection("delivery_status")}</h3><p>{deliveryCount ? `${deliveryCount} dokumen pengiriman terhubung` : "Menunggu proses gudang"}</p></div><i aria-hidden="true"/></article><article data-tone={invoiceState === "invoiced" ? "done" : invoiceState === "no" ? "idle" : invoiceState === "upselling" ? "warn" : "work"}><div className="toova-sales-process-icon"><FileText/></div><div><span>Penagihan</span><h3>{selection("invoice_status")}</h3><p>{invoiceCount ? `${invoiceCount} faktur pelanggan terhubung` : "Belum ada faktur pelanggan"}</p></div><i aria-hidden="true"/></article></div><aside><div><CircleDollarSign/><span><small>Total pesanan</small><strong>{money("amount_total")}</strong></span></div><div><CalendarDays/><span><small>Janji kirim</small><strong>{values.commitment_date ? new Date(String(values.commitment_date).replace(" ", "T") + "Z").toLocaleDateString("id-ID", { dateStyle: "medium" }) : "Belum ditentukan"}</strong></span></div></aside></div>)}
        {section("Catatan", "Syarat dan informasi yang ikut pada dokumen penjualan.", <div className="toova-sales-grid">{field("note", "wide")}</div>)}
      </>}

      {tab === "items" && <>{section("Produk dan layanan", "Pilih variant. Harga, pajak, satuan, dan subtotal dihitung Odoo.", <div className="toova-sales-lines">{field("order_line", "table")}</div>)}<section className="toova-sales-totals"><dl><div><dt>Subtotal</dt><dd>{money("amount_untaxed")}</dd></div><div><dt>Pajak</dt><dd>{money("amount_tax")}</dd></div><div className="total"><dt>Total</dt><dd>{money("amount_total")}</dd></div></dl></section></>}

      {tab === "delivery" && section("Pengiriman", "Dokumen gudang yang dibuat native dari pesanan ini.", <div className="toova-sales-related-tab"><header><div className="toova-sales-related-summary"><PackageCheck/><span><small>Status keseluruhan</small><strong>{selection("delivery_status")}</strong></span></div><div><small>Janji kirim</small><strong>{values.commitment_date ? new Date(String(values.commitment_date).replace(" ", "T") + "Z").toLocaleDateString("id-ID", { dateStyle: "medium" }) : "Belum ditentukan"}</strong></div></header>{related("deliveries")?.items.length ? <div className="toova-sales-related-list">{related("deliveries")!.items.map((item) => <article key={item.id}><div><PackageCheck/><span><strong>{item.label}</strong><small>{item.status || "Status belum tersedia"}</small></span></div><Button type="button" variant="outline" onClick={() => openRelated(related("deliveries")!.actionXmlid, item.id)}>Buka pengiriman<ArrowUpRight/></Button></article>)}</div> : <div className="toova-sales-related-empty"><PackageCheck/><strong>Belum ada pengiriman</strong><span>Dokumen muncul setelah pesanan dikonfirmasi dan procurement membuat operasi gudang.</span></div>}</div>)}

      {tab === "invoice" && section("Faktur & pembayaran", "Dokumen Keuangan yang diturunkan dari item pesanan.", <div className="toova-sales-related-tab"><header><div className="toova-sales-related-summary"><FileText/><span><small>Status penagihan</small><strong>{selection("invoice_status")}</strong></span></div><div><small>Total pesanan</small><strong>{money("amount_total")}</strong></div></header>{related("invoices")?.items.length ? <div className="toova-sales-related-list">{related("invoices")!.items.map((item) => <article key={item.id}><div><FileText/><span><strong>{item.label}</strong><small>{item.status || "Status pembayaran belum tersedia"}</small></span></div><Button type="button" variant="outline" onClick={() => openRelated(related("invoices")!.actionXmlid, item.id)}>Buka faktur<ArrowUpRight/></Button></article>)}</div> : <div className="toova-sales-related-empty"><FileText/><strong>Belum ada faktur</strong><span>Gunakan aksi Buat faktur saat pesanan sudah memenuhi kebijakan penagihan.</span></div>}</div>)}

      {tab === "settings" && <>{section("Harga & penagihan", "Aturan komersial yang memengaruhi perhitungan transaksi.", <div className="toova-sales-grid">{field("pricelist_id")}{field("payment_term_id")}{field("fiscal_position_id")}</div>)}{section("Pemenuhan", "Gudang, kebijakan pengiriman, dan komitmen operasional.", <div className="toova-sales-grid">{field("warehouse_id")}{field("picking_policy")}{field("commitment_date")}</div>)}{section("Kepemilikan & perdagangan", "Penanggung jawab internal dan syarat pengiriman internasional.", <div className="toova-sales-grid">{field("user_id")}{field("team_id")}{field("incoterm")}{field("incoterm_location")}</div>)}</>}
    </main>
  </div>;
}
