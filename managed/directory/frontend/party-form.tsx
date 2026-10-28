import { ArrowLeft, Building2, Landmark, MapPin, Save, UserRound } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@luma/components/ui/button";
import { FieldEditor, FieldValue } from "@luma/views/field-registry";
import { modifierActive } from "@luma/views/modifiers";
import type { CustomFormViewProps } from "@luma/views/view-registry";
import type { FieldSchema } from "@luma/views/types";

type Tab = "summary" | "addresses" | "contacts" | "commercial" | "tax";
type Kind = "customer" | "vendor";

export default function PartyForm(props: CustomFormViewProps & { kind: Kind }) {
  const { schema, basePath, id, values, editing, saving, onEdit, onChange, onSave, kind } = props;
  const [tab, setTab] = useState<Tab>("summary");
  const customer = kind === "customer";
  const noun = customer ? "Pelanggan" : "Vendor";
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const rows = (name: string) => Array.isArray(values[name]) ? values[name] as Record<string, unknown>[] : [];
  const addressCount = rows("managed_address_ids").filter((row) => row.active !== false).length;
  const contactCount = rows("child_ids").filter((row) => row.active !== false).length;
  const bankCount = rows("bank_ids").filter((row) => row.active !== false).length;

  const field = (name: string, className = "") => {
    const meta = fields[name];
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const readonly = Boolean(meta.readonly) || modifierActive(meta.modifiers, "readonly", values);
    const required = Boolean(meta.required) || modifierActive(meta.modifiers, "required", values);
    return <label className={`luma-customer-field ${className}`} title={meta.help}>
      <span>{meta.label}{required && <b>*</b>}</span>
      <div>{editing && !readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div>
    </label>;
  };

  const section = (title: string, description: string, content: JSX.Element) => <section className="luma-customer-section"><header><h2>{title}</h2><p>{description}</p></header>{content}</section>;
  const image = fields.image_1920 ? <div className="luma-customer-field"><span className="sr-only">Logo</span><div>{editing ? <FieldEditor actionId={schema.id} field={fields.image_1920} value={values.image_1920} onChange={(value) => onChange("image_1920", value)}/> : <FieldValue field={fields.image_1920} value={values.image_1920} record={values}/>}</div></div> : null;
  const tabs: [Tab, string, number?][] = [["summary", "Ringkasan"], ["addresses", "Alamat", addressCount], ["contacts", "Kontak/PIC", contactCount], ["commercial", customer ? "Penjualan & Keuangan" : "Pembelian & Keuangan"], ["tax", customer ? "Pajak & Coretax" : "Pajak & Bank", customer ? undefined : bankCount]];
  const indonesia = Array.isArray(values.country_id) && values.country_id[1] === "Indonesia";
  const addressFields = <div className="luma-customer-grid">{field("managed_address_text", "wide")}{field("country_id")}{field("state_id")}{indonesia && field("managed_indonesia_regency_id")}{indonesia && field("managed_indonesia_district_id")}{indonesia && field("managed_indonesia_village_id")}{!indonesia && field("city")}{field("zip")}</div>;

  return <div className="luma-customer">
    <header className="luma-customer-header">
      <div className="luma-customer-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div className="luma-customer-avatar">{values.company_type === "person" ? <UserRound/> : <Building2/>}</div><div><span>{noun}</span><h1>{id ? String(values.name || values.display_name || noun) : `${noun} baru`}</h1><p>{values.company_type === "person" ? "Individu" : "Perusahaan"} · {values.active === false ? "Diarsipkan" : "Aktif"}</p></div></div>
      <div className="luma-customer-actions">{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div>
    </header>

    <nav className="luma-customer-tabs" aria-label={`Bagian ${noun.toLowerCase()}`}>{tabs.map(([key, label, count]) => <button key={key} type="button" className={tab === key ? "active" : undefined} onClick={() => setTab(key)}>{label}{count !== undefined && <i>{count}</i>}</button>)}</nav>

    <main className="luma-customer-body">
      {tab === "summary" && <>
        {section(`Identitas ${noun.toLowerCase()}`, `Identitas legal dan kanal komunikasi utama ${noun.toLowerCase()}.`, <div className="luma-customer-overview"><div className="luma-customer-logo">{image}</div><div className="luma-customer-grid">{field("company_type")}{field("name")}{field("email")}{field("phone")}{field("mobile")}{field("website")}{field("lang")}{field("category_id")}</div></div>)}
        {section("Alamat utama", customer ? "Fallback penagihan dan pengiriman jika belum ada alamat khusus." : "Alamat legal dan korespondensi utama untuk purchase order dan vendor bill.", addressFields)}
        {section("Catatan internal", `Informasi operasional yang tidak dicetak ke dokumen ${noun.toLowerCase()}.`, <div className="luma-customer-grid">{field("comment", "wide")}</div>)}
      </>}
      {tab === "addresses" && <>
        <div className="luma-customer-fallback"><MapPin/><div><strong>Alamat utama</strong><span>{[values.street, values.street2, values.city, Array.isArray(values.state_id) ? values.state_id[1] : false, values.zip, Array.isArray(values.country_id) ? values.country_id[1] : false].filter(Boolean).join(", ") || "Belum dilengkapi"}</span><small>{customer ? "Dipakai sebagai fallback billing dan shipping." : "Dipakai sebagai alamat legal dan korespondensi default."}</small></div></div>
        {section(customer ? "Alamat tagihan & pengiriman" : "Cabang & lokasi vendor", customer ? "Satu alamat dapat dipakai untuk billing, shipping, atau keduanya. Default dipilih otomatis pada Sales Order." : "Simpan kantor cabang, lokasi pengambilan, atau alamat pengembalian. Lokasi penerimaan barang tetap warehouse perusahaan.", <div className="luma-customer-relation">{field("managed_address_ids")}</div>)}
      </>}
      {tab === "contacts" && section("Kontak/PIC", `Orang yang bekerja pada ${noun.toLowerCase()} ini. Data PIC terpisah dari alamat.`, <div className="luma-customer-relation">{field("child_ids")}</div>)}
      {tab === "commercial" && section(customer ? "Penjualan & keuangan" : "Pembelian & keuangan", "Default transaksi tetap dihitung oleh engine Odoo.", <div className="luma-customer-grid">{customer ? <>{field("user_id")}{field("property_product_pricelist")}{field("property_payment_term_id")}</> : <>{field("property_supplier_payment_term_id")}{field("property_purchase_currency_id")}{field("property_account_position_id")}{field("receipt_reminder_email")}{field("reminder_date_before_receipt")}</>}</div>)}
      {tab === "tax" && <>
        {section(customer ? "Pajak & Coretax" : "Pajak vendor", customer ? "Identitas pajak berada pada customer utama, bukan alamat pengiriman." : "Identitas pajak berada pada vendor utama, bukan PIC atau lokasi cabang.", <div className="luma-customer-grid">{field("l10n_id_pkp")}{field("vat")}{field("l10n_id_nik")}{field("l10n_id_tku")}{field("l10n_id_buyer_document_type")}{field("l10n_id_buyer_document_number")}{field("l10n_id_tax_name")}{field("l10n_id_tax_address", "wide")}{customer && field("l10n_id_kode_transaksi")}</div>)}
        {!customer && section("Rekening pembayaran", "Rekening resmi vendor untuk pembayaran keluar. Verifikasi perubahan rekening di luar sistem sebelum membayar.", <div className="luma-customer-relation"><div className="luma-vendor-bank-heading"><Landmark/><span>{bankCount} rekening aktif</span></div>{field("bank_ids")}</div>)}
      </>}
    </main>
  </div>;
}
