import { ArrowUpRight, Check, FileText, PackageCheck, Save, ShoppingCart, UserRound } from "lucide-react";
import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { DocumentRelations } from "@toova/components/document-relations";
import { ManagedFormSection, ManagedFormShell } from "@toova/components/managed-form";
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
  const processState = String(values.managed_process_status || (quotation ? "quotation" : "fulfillment"));
  const processSteps = quotation
    ? [["quotation", "Penawaran"]]
    : [["fulfillment", "Pengiriman"], ["invoicing", "Faktur"], ["payment", "Pembayaran"], ["complete", "Selesai"]];
  const selection = (name: string) => fields[name]?.selection?.find(([key]) => key === values[name])?.[1] || "Belum diproses";
  const processIndex = Math.max(0, processSteps.findIndex(([key]) => key === processState));
  const processComplete = processState === "complete";
  const processLabel = quotation ? selection("state") : selection("managed_process_status");
  const processMessage = processState === "complete" ? "Pesanan terpenuhi dan pembayaran lunas."
    : processState === "payment" ? "Menunggu pelunasan faktur pelanggan."
    : processState === "invoicing" ? "Pengiriman selesai; faktur belum dibuat."
    : processState === "fulfillment" ? "Pesanan sedang dipenuhi oleh gudang."
    : "Pesanan belum dikonfirmasi.";
  const completedSteps = processComplete ? processSteps.length : processIndex;
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
  const value = (name: string) => fields[name] ? <FieldValue field={fields[name]} value={values[name]} record={values}/> : <>—</>;
  const section = (title: string, description: string, content: JSX.Element) => <ManagedFormSection title={title} description={description} className="toova-sales-section">{content}</ManagedFormSection>;
  const tabs: [Tab, string, number?][] = quotation
    ? [["summary", "Ringkasan"], ["items", "Item", itemCount], ["settings", "Pengaturan"]]
    : [["summary", "Ringkasan"], ["items", "Item", itemCount], ["delivery", "Pengiriman", deliveryCount], ["invoice", "Faktur", invoiceCount], ["settings", "Pengaturan"]];

  const badge = id && status ? <div className={`toova-sales-state ${processComplete ? "complete" : ""}`}><button type="button" aria-label={`Status pesanan: ${processLabel}`}>{processLabel}</button><div role="tooltip"><span>{quotation ? "Perjalanan dokumen" : "Progres bisnis"}</span><ol>{(quotation ? statusOptions : processSteps).map(([key, label], index) => { const current = quotation ? statusIndex : processIndex; return <li key={key} className={index < current || (!quotation && processComplete) ? "completed" : index === current ? "current" : undefined}><i>{index < current || (!quotation && processComplete) ? <Check/> : index + 1}</i><b>{label}</b></li>; })}</ol>{!quotation && <p>Dokumen: {selection("state")}{values.state === "done" ? " · tidak dapat diedit" : " · tetap aktif"}</p>}</div></div> : undefined;
  const actions = <><DocumentRelations groups={relatedDocuments}/>{id && secondaryButtons.map((button) => <Button key={`${button.type}:${button.name}`} variant="outline" onClick={() => onButton(button.name, button.type)}>{button.label}</Button>)}{id && primaryButton && <Button onClick={() => onButton(primaryButton.name, primaryButton.type)}>{primaryButton.label}</Button>}{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : schema.form.write && <Button variant="outline" onClick={onEdit}>Edit</Button>)}</>;

  return <ManagedFormShell icon={<ShoppingCart/>} title={id ? String(values.name || "Pesanan") : "Penawaran baru"} subtitle={customer} badge={badge} actions={actions} tabs={tabs.map(([key, label, count]) => ({ key, label, count }))} activeTab={tab} onTabChange={setTab} onBack={onBack} className="toova-sales-document">
      {tab === "summary" && <>
        {section("Pelanggan", "Identitas, alamat, dan referensi transaksi.", <div className="toova-sales-overview"><div className="toova-sales-customer"><UserRound/><div><span>Pelanggan</span><h3>{customer}</h3></div></div><div className="toova-sales-grid">{field("partner_id")}{field("client_order_ref")}{field("partner_invoice_id")}{field("partner_shipping_id")}{field("date_order")}{quotation && field("validity_date")}</div></div>)}
        {section("Detail pesanan", "Nilai dan konteks utama untuk mengambil keputusan.", <div className="toova-sales-facts"><article className="primary"><span>Total pesanan</span><strong>{money("amount_total")}</strong><small>Subtotal {money("amount_untaxed")} · Pajak {money("amount_tax")}</small></article><article><span>Tanggal pesanan</span><strong>{value("date_order")}</strong><small>{values.client_order_ref ? `Ref. ${values.client_order_ref}` : "Tanpa referensi pelanggan"}</small></article><article><span>Janji kirim</span><strong>{value("commitment_date")}</strong><small>{selection("picking_policy")}</small></article><article><span>Penanggung jawab</span><strong>{value("user_id")}</strong><small>{Array.isArray(values.team_id) ? String(values.team_id[1]) : "Tanpa tim penjualan"}</small></article></div>)}
        {!quotation && section("Progres pesanan", "Status bisnis dari pengiriman sampai pembayaran.", <div className={`toova-sales-process ${processComplete ? "complete" : ""}`}><header><div><span>{processComplete ? <Check/> : <PackageCheck/>}</span><div><h3>{processLabel}</h3><p>{processMessage}</p></div></div><b>{completedSteps}/{processSteps.length}</b></header><div className="toova-sales-process-stepper-wrap"><div className="toova-sales-process-stepper">{processSteps.map(([key, label], index) => <article key={key} className={index < processIndex || processComplete ? "completed" : index === processIndex ? "current" : "upcoming"}><i>{index < processIndex || processComplete ? <Check/> : index + 1}</i><span>{label}</span></article>)}</div></div></div>)}
        {section("Catatan", "Syarat dan informasi yang ikut pada dokumen penjualan.", <div className="toova-sales-grid">{field("note", "wide")}</div>)}
      </>}

      {tab === "items" && <>{section("Produk dan layanan", "Pilih variant. Harga, pajak, satuan, dan subtotal dihitung Odoo.", <div className="toova-sales-lines">{field("order_line", "table")}</div>)}<section className="toova-sales-totals"><dl><div><dt>Subtotal</dt><dd>{money("amount_untaxed")}</dd></div><div><dt>Pajak</dt><dd>{money("amount_tax")}</dd></div><div className="total"><dt>Total</dt><dd>{money("amount_total")}</dd></div></dl></section></>}

      {tab === "delivery" && section("Pengiriman", "Dokumen gudang yang dibuat native dari pesanan ini.", <div className="toova-sales-related-tab"><header><div className="toova-sales-related-summary"><PackageCheck/><span><small>Status keseluruhan</small><strong>{selection("delivery_status")}</strong></span></div><div><small>Janji kirim</small><strong>{values.commitment_date ? new Date(String(values.commitment_date).replace(" ", "T") + "Z").toLocaleDateString("id-ID", { dateStyle: "medium" }) : "Belum ditentukan"}</strong></div></header>{related("deliveries")?.items.length ? <div className="toova-sales-related-list">{related("deliveries")!.items.map((item) => <article key={item.id}><div><PackageCheck/><span><strong>{item.label}</strong><small>{item.status || "Status belum tersedia"}</small></span></div><Button type="button" variant="outline" onClick={() => openRelated(related("deliveries")!.actionXmlid, item.id)}>Buka pengiriman<ArrowUpRight/></Button></article>)}</div> : <div className="toova-sales-related-empty"><PackageCheck/><strong>Belum ada pengiriman</strong><span>Dokumen muncul setelah pesanan dikonfirmasi dan procurement membuat operasi gudang.</span></div>}</div>)}

      {tab === "invoice" && section("Faktur & pembayaran", "Dokumen Keuangan yang diturunkan dari item pesanan.", <div className="toova-sales-related-tab"><header><div className="toova-sales-related-summary"><FileText/><span><small>Status penagihan</small><strong>{selection("invoice_status")}</strong></span></div><div><small>Total pesanan</small><strong>{money("amount_total")}</strong></div></header>{related("invoices")?.items.length ? <div className="toova-sales-related-list">{related("invoices")!.items.map((item) => <article key={item.id}><div><FileText/><span><strong>{item.label}</strong><small>{item.status || "Status pembayaran belum tersedia"}</small></span></div><Button type="button" variant="outline" onClick={() => openRelated(related("invoices")!.actionXmlid, item.id)}>Buka faktur<ArrowUpRight/></Button></article>)}</div> : <div className="toova-sales-related-empty"><FileText/><strong>Belum ada faktur</strong><span>Gunakan aksi Buat faktur saat pesanan sudah memenuhi kebijakan penagihan.</span></div>}</div>)}

      {tab === "settings" && <>{section("Harga & penagihan", "Aturan komersial yang memengaruhi perhitungan transaksi.", <div className="toova-sales-grid">{field("pricelist_id")}{field("payment_term_id")}{field("fiscal_position_id")}</div>)}{section("Pemenuhan", "Gudang, kebijakan pengiriman, dan komitmen operasional.", <div className="toova-sales-grid">{field("warehouse_id")}{field("picking_policy")}{field("commitment_date")}</div>)}{section("Kepemilikan & perdagangan", "Penanggung jawab internal dan syarat pengiriman internasional.", <div className="toova-sales-grid">{field("user_id")}{field("team_id")}{field("incoterm")}{field("incoterm_location")}</div>)}</>}
  </ManagedFormShell>;
}
