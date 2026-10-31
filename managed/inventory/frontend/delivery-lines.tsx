import { useState } from "react";
import { createPortal } from "react-dom";
import { Pencil, X } from "lucide-react";
import { Button } from "@toova/components/ui/button";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import type { FieldSchema } from "@toova/views/types";

type Row = Record<string, unknown>;
type Props = { actionId: number; field: FieldSchema; value: unknown; parentValues?: Record<string, unknown>; onChange: (value: unknown) => void };
const relationLabel = (value: unknown) => Array.isArray(value) ? String(value[1]) : "—";

export default function DeliveryLines({ actionId, field, value, parentValues = {}, onChange }: Props) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const columns = field.relationView?.columns || [];
  const byName = Object.fromEntries(columns.map((column) => [column.name, column])) as Record<string, FieldSchema>;
  const [open, setOpen] = useState<number>();
  const [draft, setDraft] = useState<Row>();
  const close = () => { setOpen(undefined); setDraft(undefined); };
  const editable = field.name === "managed_move_line_ids";
  const edit = (index: number) => { if (editable) { setOpen(index); setDraft({ ...rows[index] }); } };
  const save = () => { if (open === undefined || !draft) return; onChange(rows.map((row, index) => index === open ? draft : row)); close(); };
  const fieldControl = (name: string) => {
    const meta = byName[name];
    if (!meta || !draft) return null;
    return <label><span>{meta.label}</span><FieldEditor actionId={actionId} field={meta} value={draft[name]} parentValues={{ ...parentValues, ...draft }} onChange={(next) => setDraft((current) => ({ ...(current || {}), [name]: next }))}/></label>;
  };
  return <div className="toova-delivery-lines">
    <div className="overflow-x-auto"><table><thead><tr><th>Produk / Variant</th><th>Diminta</th><th>Direservasi</th><th>Selesai</th><th>Sisa</th><th>Lot / Serial</th>{editable && <th/>}</tr></thead><tbody>{rows.map((row, index) => { const demand = Number(row.managed_demand_qty ?? row.product_uom_qty ?? 0); const done = Number(row.qty_done ?? row.quantity_done ?? 0); const reserved = Number(row.reserved_uom_qty ?? row.reserved_availability ?? 0); return <tr key={String(row.id || index)}><td><strong>{relationLabel(row.product_id)}</strong><small>{relationLabel(row.product_uom_id ?? row.product_uom)}</small></td><td>{demand.toLocaleString("id-ID")}</td><td>{reserved.toLocaleString("id-ID")}</td><td>{done.toLocaleString("id-ID")}</td><td>{Math.max(demand - done, 0).toLocaleString("id-ID")}</td><td>{relationLabel(row.lot_id) !== "—" ? relationLabel(row.lot_id) : String(row.lot_name || "—")}</td>{editable && <td><button type="button" onClick={() => edit(index)} aria-label="Isi jumlah selesai dan lot"><Pencil/></button></td>}</tr>; })}</tbody></table></div>
    {!rows.length && <span className="workspace-relation-empty">Belum ada operasi pengiriman.</span>}
    {open !== undefined && draft && createPortal(<div className="managed-relation-editor-backdrop" role="presentation"><section className="managed-relation-editor" role="dialog" aria-modal="true"><header><div><h3>{relationLabel(draft.product_id)}</h3><p>Isi jumlah selesai. Lot/serial wajib mengikuti tracking produk.</p></div><button type="button" onClick={close} aria-label="Tutup"><X/></button></header><main>{fieldControl("qty_done")}{fieldControl("lot_id")}{fieldControl("lot_name")}</main><footer><Button type="button" variant="ghost" onClick={close}>Batal</Button><Button type="button" onClick={save}>Simpan</Button></footer></section></div>, document.body)}
  </div>;
}
