import { ArrowLeft, Box, CalendarClock, CheckCircle2, MapPin, PackageCheck, Save, ScanLine, Truck } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@toova/components/ui/button";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import { modifierActive } from "@toova/views/modifiers";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

export default function DeliveryForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave, onButton }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const done = values.state === "done";
  const cancelled = values.state === "cancel";
  const editable = !done && !cancelled;
  const visibleButtons = schema.form.buttons.filter((button) => !modifierActive(button.modifiers, "invisible", values));
  const primaryButton = visibleButtons.find((button) => button.primary);
  const secondaryButtons = visibleButtons.filter((button) => !button.primary);
  const stateLabel = fields.state?.selection?.find(([key]) => key === values.state)?.[1] || String(values.state || "Draf");
  const moveLines = Array.isArray(values.managed_move_line_ids) ? values.managed_move_line_ids.length : 0;
  const demandLines = Array.isArray(values.move_ids_without_package) ? values.move_ids_without_package.length : 0;
  const field = (name: string, className = "") => {
    const meta = fields[name];
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const writable = editing && editable && !meta.readonly;
    return <label className={`toova-delivery-field ${className}`}><span>{meta.label}{meta.required && <b>*</b>}</span><div>{writable ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>;
  };

  return <div className="toova-delivery-document">
    <header className="toova-finance-header"><div className="toova-finance-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div className="toova-delivery-mark"><Truck/></div><div><h1>{id ? String(values.name || "Pengiriman") : "Pengiriman"}</h1><p>{String(values.origin || "Tanpa pesanan sumber")}</p></div></div><div className="toova-finance-actions">{id && <Button asChild variant="outline"><Link to={`/app/persediaan/operasi-gudang?task=${id}`}><ScanLine/>Mode Gudang</Link></Button>}{id && secondaryButtons.map((button) => <Button key={`${button.type}:${button.name}`} variant="outline" onClick={() => onButton(button.name, button.type)}>{button.label}</Button>)}{id && primaryButton && <Button onClick={() => onButton(primaryButton.name, primaryButton.type)}>{primaryButton.label}</Button>}{editable && schema.form.write && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit jadwal</Button>)}</div></header>

    <div className="toova-delivery-status"><span data-tone={done ? "done" : cancelled ? "warn" : "work"}>{done ? <CheckCircle2/> : <PackageCheck/>}<i>Status pengiriman</i><b>{stateLabel}</b></span><span><CalendarClock/><i>Jadwal</i><b>{values.scheduled_date ? new Date(String(values.scheduled_date).replace(" ", "T") + "Z").toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" }) : "Belum dijadwalkan"}</b></span><span><Box/><i>Operasi</i><b>{moveLines || demandLines} baris produk</b></span></div>

    <main className="toova-delivery-body"><section className="toova-delivery-overview"><div className="toova-delivery-address"><MapPin/><div><span>Dikirim ke</span><h2>{Array.isArray(values.partner_id) ? String(values.partner_id[1]) : "Alamat belum ditentukan"}</h2><p>{String(values.products_availability || "Ketersediaan belum dihitung")}</p></div></div><div className="toova-delivery-meta">{field("scheduled_date")}{field("date_deadline")}{field("date_done")}{field("picking_type_id")}{field("location_id")}{field("location_dest_id")}</div></section>

      <section className="toova-delivery-operations"><header><div><h2>Barang yang diproses</h2><p>Diminta, reservasi, selesai, sisa, dan lot/serial dalam satu tabel kerja.</p></div><b>{moveLines || demandLines} produk</b></header>{field(moveLines ? "managed_move_line_ids" : "move_ids_without_package", "operations")}</section>
      <section className="toova-delivery-notes">{field("note")}</section>
    </main>
  </div>;
}
