import { Box, PackageCheck, Save, TrendingUp, Wrench } from "lucide-react";
import { useState } from "react";
import { Button } from "@toova/components/ui/button";
import { ManagedFormSection, ManagedFormShell } from "@toova/components/managed-form";
import { FieldEditor, FieldValue, registerFieldEditor, registerFieldRenderer } from "@toova/views/field-registry";
import { AttributeLinesEditor, AttributeLinesValue, VariantsEditor, VariantsValue } from "./variant-manager";
import { modifierActive } from "@toova/views/modifiers";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

type Tab = "summary" | "variants" | "sales" | "purchase" | "inventory" | "accounting";

registerFieldEditor("managed_attribute_lines", (props) => <AttributeLinesEditor {...props}/>);
registerFieldRenderer("managed_attribute_lines", ({ value }) => <AttributeLinesValue value={value}/>);
registerFieldEditor("managed_variants", (props) => <VariantsEditor {...props}/>);
registerFieldRenderer("managed_variants", ({ value, record }) => <VariantsValue value={value} parentValues={record}/>);

function InventoryMetric({ icon, label, value, unit, detail, tone }: { icon: JSX.Element; label: string; value: unknown; unit: string; detail: string; tone?: "forecast" }) {
  const quantity = typeof value === "number" ? value : Number(value || 0);
  return <article className={tone === "forecast" ? "forecast" : undefined}>
    <div className="toova-product-metric-icon">{icon}</div>
    <div className="toova-product-metric-copy"><span>{label}</span><strong>{Number.isFinite(quantity) ? quantity.toLocaleString("id-ID", { maximumFractionDigits: 2 }) : "0"}<small>{unit}</small></strong><p>{detail}</p></div>
  </article>;
}

export default function ProductForm(props: CustomFormViewProps) {
  const { schema, id, values, editing, saving, onEdit, onChange, onSave, onBack } = props;
  const [tab, setTab] = useState<Tab>("summary");
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const service = values.managed_product_kind === "service" || values.detailed_type === "service";
  const stocked = !service && Boolean(values.managed_track_inventory ?? values.detailed_type === "product");
  const supplierCount = Array.isArray(values.seller_ids) ? values.seller_ids.filter((row) => typeof row !== "object" || row === null || !("active" in row) || row.active !== false).length : 0;

  const field = (name: string, className = "") => {
    const meta = fields[name];
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const readonly = Boolean(meta.readonly) || modifierActive(meta.modifiers, "readonly", values);
    const required = Boolean(meta.required) || modifierActive(meta.modifiers, "required", values);
    return <label className={`managed-form-field ${className}`} title={meta.help}><span>{meta.label}{required && <b>*</b>}</span><div>{editing && !readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>;
  };
  const section = (title: string, description: string, content: JSX.Element) => <ManagedFormSection title={title} description={description}>{content}</ManagedFormSection>;
  const image = fields.image_1920 ? <div className="managed-form-field"><span className="sr-only">Gambar produk</span><div>{editing ? <FieldEditor actionId={schema.id} field={fields.image_1920} value={values.image_1920} onChange={(value) => onChange("image_1920", value)}/> : <FieldValue field={fields.image_1920} value={values.image_1920} record={values}/>}</div></div> : null;
  const variantRows = Array.isArray(values.product_variant_ids) ? values.product_variant_ids as Record<string, unknown>[] : [];
  const variantCount = variantRows.filter((row) => row.active !== false).length;
  const tabs: [Tab, string, number?][] = [["summary", "Ringkasan"], ["variants", "Variants", variantCount], ["sales", "Penjualan"], ["purchase", "Pembelian", supplierCount], ["inventory", "Persediaan"], ["accounting", "Pajak & Accounting"]];
  const typeLabel = service ? "Jasa" : stocked ? "Barang dengan stok" : "Barang tanpa stok";
  const unitLabel = Array.isArray(values.uom_id) ? String(values.uom_id[1]) : "unit";
  const inventoryStatus = <div className={`toova-product-stock-status ${stocked ? "tracked" : "untracked"}`}><i/><div><strong>{stocked ? "Pelacakan stok aktif" : "Pelacakan stok nonaktif"}</strong><span>{stocked ? "Kuantitas berubah dari penerimaan, pengiriman, dan penyesuaian stok." : "Produk tetap dapat dibeli dan dijual, tetapi kuantitas gudang tidak dicatat."}</span></div></div>;
  const inventoryMetrics = <div className="toova-product-inventory-summary">{inventoryStatus}<div className="toova-product-metrics"><InventoryMetric icon={<PackageCheck/>} label="On hand" value={values.qty_available} unit={unitLabel} detail={stocked ? "Stok fisik tersedia saat ini" : "Tidak dihitung untuk barang tanpa stok"}/><InventoryMetric icon={<TrendingUp/>} label="Forecast" value={values.virtual_available} unit={unitLabel} detail={stocked ? "On hand + masuk − keluar" : "Tidak dihitung untuk barang tanpa stok"} tone="forecast"/></div></div>;

  const actions = (id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>);
  return <ManagedFormShell icon={service ? <Wrench/> : stocked ? <PackageCheck/> : <Box/>} title={id ? String(values.name || "Produk") : "Produk baru"} subtitle={`${typeLabel} · ${values.active === false ? "Diarsipkan" : "Aktif"}`} actions={actions} tabs={tabs.map(([key, label, count]) => ({ key, label, count }))} activeTab={tab} onTabChange={setTab} onBack={onBack} className="toova-customer toova-product">
      {tab === "summary" && <>{section("Identitas produk", "Data utama untuk pencarian, transaksi, dan dokumen.", <div className="toova-customer-overview"><div className="toova-customer-logo">{image}</div><div className="managed-form-grid">{field("name")}{field("default_code")}{field("barcode")}{field("managed_product_kind")}{!service && field("managed_track_inventory")}{field("categ_id")}{field("active")}</div></div>)}{section("Satuan & ukuran", "Satuan transaksi dan ukuran fisik produk.", <div className="managed-form-grid">{field("uom_id")}{field("uom_po_id")}{!service && field("weight")}{!service && field("volume")}</div>)}{section("Catatan internal", "Informasi internal yang tidak dikirim ke customer atau vendor.", <div className="managed-form-grid">{field("description", "wide")}</div>)}</>}
      {tab === "variants" && <>{section("Atribut & kombinasi", "Pilih atribut dan nilai. Odoo membuat kombinasi product.product native.", <div className="managed-form-relation">{field("attribute_line_ids")}</div>)}{id && section("Variants", "Kelola identity, harga, ukuran, dan stok per kombinasi.", <div className="managed-form-relation">{field("product_variant_ids")}</div>)}</>}
      {tab === "sales" && <>{section("Kebijakan penjualan", "Default harga dan penagihan tetap dihitung engine Odoo.", <div className="managed-form-grid">{field("sale_ok")}{field("list_price")}{field("invoice_policy")}{!service && field("sale_delay")}{field("taxes_id")}</div>)}{section("Deskripsi penjualan", "Teks ini masuk ke quotation dan sales order.", <div className="managed-form-grid">{field("description_sale", "wide")}</div>)}</>}
      {tab === "purchase" && <>{section("Kebijakan pembelian", "Cost default dipakai saat harga vendor tidak ditemukan.", <div className="managed-form-grid">{field("purchase_ok")}{field("standard_price")}{field("purchase_method")}{field("supplier_taxes_id")}</div>)}{section("Vendor & harga beli", "Harga, minimum pembelian, kode vendor, dan lead time canonical Odoo.", <div className="managed-form-relation">{field("seller_ids")}</div>)}{section("Deskripsi pembelian", "Teks ini masuk ke RFQ dan purchase order.", <div className="managed-form-grid">{field("description_purchase", "wide")}</div>)}</>}
      {tab === "inventory" && (service ? <div className="toova-product-empty"><Wrench/><strong>Jasa tidak memiliki persediaan</strong><span>Ubah tipe produk jika barang perlu penerimaan, pengiriman, atau stok.</span></div> : <>{section("Status persediaan", "Ringkasan kuantitas produk pada seluruh lokasi internal perusahaan.", inventoryMetrics)}{section("Operasional gudang", "Aktifkan barang dengan stok untuk route dan tracking inventory.", <div className="managed-form-grid">{field("route_ids", "wide")}{field("responsible_id")}{field("tracking")}</div>)}</>)}
      {tab === "accounting" && <>{section("Pajak & Coretax", "Mapping pajak transaksi dan kode produk Coretax.", <div className="managed-form-grid">{field("taxes_id")}{field("supplier_taxes_id")}{field("l10n_id_product_code")}</div>)}{section("Akun produk", "Kosongkan untuk memakai akun default kategori produk.", <div className="managed-form-grid">{field("property_account_income_id")}{field("property_account_expense_id")}</div>)}</>}
  </ManagedFormShell>;
}
