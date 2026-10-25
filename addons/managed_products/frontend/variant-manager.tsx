import { Image, Pencil, Plus, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@luma/components/ui/button";
import { FieldEditor } from "@luma/views/field-registry";
import type { FieldSchema } from "@luma/views/types";

type Row = Record<string, unknown>;
type Props = { actionId: number; field: FieldSchema; value: unknown; parentValues?: Row; onChange: (value: unknown) => void };
const relationLabel = (value: unknown) => Array.isArray(value) ? String(value[1]) : "";
const relationIds = (value: unknown) => Array.isArray(value) ? value.map((item) => Array.isArray(item) ? Number(item[0]) : Number(item)) : [];
const currency = (value: unknown) => Number(value || 0).toLocaleString("id-ID", { maximumFractionDigits: 2 });

export function AttributeLinesEditor({ actionId, field, value, parentValues, onChange }: Props) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const columns = Object.fromEntries((field.relationView?.columns || []).map((column) => [column.name, column])) as Record<string, FieldSchema>;
  const active = rows.filter((row) => row.active !== false);
  const count = active.reduce((total, row) => {
    if (row.managed_creation_mode === "no_variant") return total;
    return total * Math.max(relationIds(row.value_ids).length, 1);
  }, active.length ? 1 : 0);
  const update = (index: number, name: string, next: unknown) => onChange(rows.map((row, position) => position === index ? { ...row, [name]: next, ...(name === "attribute_id" ? { value_ids: [], managed_value_prices: {} } : {}) } : row));
  const add = () => onChange([...rows, { active: true, value_ids: [], managed_value_prices: {} }]);
  const archive = (index: number) => onChange(rows.map((row, position) => position === index ? { ...row, active: false } : row));
  return <div className="luma-variant-config">
    <div className="luma-variant-preview"><div><strong>{count.toLocaleString("id-ID")}</strong><span>kombinasi diperkirakan</span></div><p>Odoo membuat kombinasi native setelah produk disimpan. Maksimum 1.000 instant variants.</p></div>
    <div className="luma-attribute-lines">{active.map((row) => { const index = rows.indexOf(row); const prices = (row.managed_value_prices && typeof row.managed_value_prices === "object" ? row.managed_value_prices : {}) as Record<string, unknown>; return <article key={String(row.id || `new-${index}`)}>
      <header><small>{row.managed_creation_mode === "dynamic" ? "Dibuat saat transaksi" : row.managed_creation_mode === "no_variant" ? "Opsi tanpa variant" : "Kombinasi dibuat saat simpan"}</small><button type="button" aria-label="Hapus atribut" onClick={() => archive(index)}><Trash2/></button></header>
      <div className="luma-attribute-line-fields"><label><span>Atribut</span><FieldEditor actionId={actionId} field={columns.attribute_id} value={row.attribute_id} parentValues={{ ...row, id: parentValues?.id }} onChange={(next) => update(index, "attribute_id", next)}/></label><label><span>Nilai</span><FieldEditor actionId={actionId} field={columns.value_ids} value={row.value_ids} parentValues={{ ...row, id: parentValues?.id }} onChange={(next) => update(index, "value_ids", next)}/></label></div>
      {Array.isArray(row.value_ids) && row.value_ids.length > 0 && <div className="luma-attribute-prices"><span>Tambahan harga per nilai</span>{row.value_ids.map((item) => { const id = String(Array.isArray(item) ? item[0] : item); return <label key={id}><span>{relationLabel(item)}</span><input type="number" min="0" value={String(prices[id] || "")} placeholder="0" onChange={(event) => update(index, "managed_value_prices", { ...prices, [id]: event.target.value === "" ? 0 : Number(event.target.value) })}/></label>; })}</div>}
    </article>; })}{!active.length && <div className="luma-variant-empty"><strong>Master atribut masih kosong</strong><span>Buat Warna, Ukuran, atau atribut lain lewat menu Products → Attributes, lalu kembali dan pilih di sini.</span></div>}</div>
    <button type="button" className="workspace-relation-add" onClick={add}><Plus/>Tambah atribut</button>
  </div>;
}

export function AttributeLinesValue({ value }: { value: unknown }) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const active = rows.filter((row) => row.active !== false);
  return <div className="luma-attribute-summary">{active.map((row, index) => <span key={String(row.id || index)}><strong>{relationLabel(row.attribute_id)}</strong>{Array.isArray(row.value_ids) ? row.value_ids.map(relationLabel).join(", ") : ""}</span>)}{!active.length && <i>Belum ada atribut</i>}</div>;
}

export function VariantsEditor({ actionId, field, value, parentValues, onChange }: Props) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const [open, setOpen] = useState<number>();
  const [draft, setDraft] = useState<Row>();
  const active = rows.filter((row) => row.active !== false);
  const multiple = active.length > 1;
  const readOnly = new Set(["managed_variant_name", "qty_available", "virtual_available", "lst_price"]);
  const editableColumns = useMemo(() => (field.relationView?.columns || []).filter((column) => !readOnly.has(column.name) && column.name !== "active"), [field]);
  const edit = (index: number) => { setOpen(index); setDraft({ ...rows[index] }); };
  const close = () => { setOpen(undefined); setDraft(undefined); };
  const save = () => { if (open === undefined || !draft) return; onChange(rows.map((row, index) => index === open ? draft : row)); close(); };
  const archive = (index: number) => onChange(rows.map((row, position) => position === index ? { ...row, active: false } : row));
  const unit = Array.isArray(parentValues?.uom_id) ? parentValues.uom_id[1] : "unit";
  return <div className="luma-variants">
    <div className="luma-variants-table"><table><thead><tr><th>Variant</th><th>SKU</th><th>Barcode</th><th>Harga ekstra</th><th>On hand</th><th>Forecast</th><th/></tr></thead><tbody>{active.map((row) => { const index = rows.indexOf(row); return <tr key={String(row.id || index)}><td><div className="luma-variant-name">{row.image_variant_1920 ? <Image/> : <span/>}<strong>{String(row.managed_variant_name || "Default")}</strong></div></td><td>{String(row.default_code || "—")}</td><td>{String(row.barcode || "—")}</td><td>{multiple ? currency(Number(row.lst_price || 0) - Number(parentValues?.list_price || 0)) : "0"}</td><td>{currency(row.qty_available)} {String(unit)}</td><td>{currency(row.virtual_available)} {String(unit)}</td><td><div className="managed-relation-card-actions"><button type="button" aria-label="Edit variant" onClick={() => edit(index)}><Pencil/></button><button type="button" aria-label="Arsipkan variant" onClick={() => archive(index)}><Trash2/></button></div></td></tr>; })}</tbody></table>{!active.length && <div className="luma-variant-empty">Variants dibuat setelah konfigurasi atribut disimpan.</div>}</div>
    {open !== undefined && draft && <div className="managed-relation-editor-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><section className="managed-relation-editor" role="dialog" aria-modal="true"><header><div><h3>{String(draft.managed_variant_name || "Variant")}</h3><p>SKU, barcode, gambar, cost, dan ukuran khusus variant.</p></div><button type="button" onClick={close} aria-label="Tutup"><X/></button></header><main>{editableColumns.map((column) => <label key={column.name} className={column.name === "image_variant_1920" ? "wide" : undefined}><span>{column.label}{column.required && <b>*</b>}</span><FieldEditor actionId={actionId} field={column} value={draft[column.name]} parentValues={{ ...draft, id: parentValues?.id }} onChange={(next) => setDraft((current) => ({ ...(current || {}), [column.name]: next }))}/></label>)}</main><footer><Button type="button" variant="ghost" onClick={close}>Batal</Button><Button type="button" onClick={save}>Simpan</Button></footer></section></div>}
  </div>;
}

export function VariantsValue({ value, parentValues }: { value: unknown; parentValues?: Row }) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const unit = Array.isArray(parentValues?.uom_id) ? parentValues.uom_id[1] : "unit";
  return <div className="luma-variants-read">{rows.filter((row) => row.active !== false).map((row, index) => <span key={String(row.id || index)}><strong>{String(row.managed_variant_name || "Default")}</strong><i>{String(row.default_code || "Tanpa SKU")}</i><b>{currency(row.qty_available)} {String(unit)}</b></span>)}</div>;
}
