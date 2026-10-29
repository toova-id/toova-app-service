import { Pencil, Plus, Trash2, X } from "lucide-react";
import { useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Button } from "@toova/components/ui/button";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import { apiMutation } from "@toova/lib/api";
import type { FieldSchema } from "@toova/views/types";

type Row = Record<string, unknown>;
type Props = { actionId: number; field: FieldSchema; value: unknown; parentValues?: Record<string, unknown>; onChange: (value: unknown) => void };

const label = (value: unknown) => Array.isArray(value) ? String(value[1]) : "";

export default function SaleOrderLines({ actionId, field, value, parentValues = {}, onChange }: Props) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const columns = field.relationView?.columns || [];
  const byName = Object.fromEntries(columns.map((column) => [column.name, column])) as Record<string, FieldSchema>;
  const [open, setOpen] = useState<number>();
  const [draft, setDraft] = useState<Row>();
  const request = useRef(0);
  const editable = (name: string) => byName[name] && !byName[name].readonly;
  const close = () => { setOpen(undefined); setDraft(undefined); };
  const add = () => { setOpen(rows.length); setDraft({ product_uom_qty: 1, managed_discount_mode: "percentage", discount: 0, managed_discount_fixed: 0 }); };
  const edit = (index: number) => { setOpen(index); setDraft({ ...rows[index] }); };
  const remove = (index: number) => onChange(rows.filter((_, position) => position !== index));
  const save = () => { if (open === undefined || !draft || !draft.product_id) return; onChange(open < rows.length ? rows.map((row, index) => index === open ? draft : row) : [...rows, draft]); close(); };
  const update = async (name: string, nextValue: unknown) => {
    const next = { ...(draft || {}), [name]: nextValue };
    if (name === "managed_discount_mode") {
      next.discount = 0;
      next.managed_discount_fixed = 0;
    }
    if (name === "product_id") {
      next.product_uom = false;
      next.tax_id = false;
    }
    setDraft(next);
    if (field.relationView?.onchange?.[name] !== "1") return;
    const current = ++request.current;
    try {
      const result = await apiMutation<{ values: Row }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}/onchange`, "POST", {
        values: next,
        parentValues: { ...parentValues, ...next },
        field: name,
      });
      if (current === request.current) setDraft((row) => ({ ...(row || {}), ...result.values }));
    } catch { /* Save remains native-server validated. */ }
  };
  const control = (name: string, wide = false) => {
    const meta = byName[name];
    if (!meta || !draft || !editable(name)) return null;
    return <label className={wide ? "wide" : undefined}><span>{meta.label}{meta.required && <b>*</b>}</span><FieldEditor actionId={actionId} field={meta} value={draft[name]} parentValues={{ ...parentValues, ...draft }} onChange={(next) => update(name, next)}/></label>;
  };
  const money = (name: "price_unit" | "price_subtotal" | "price_total", row: Row, value = row[name]) => byName[name] ? <FieldValue field={byName[name]} value={value} record={row}/> : <>—</>;
  return <div className="toova-sale-lines">
    <div className="toova-sale-line-list">
      {rows.map((row, index) => { const discount = Number(row.discount || 0); const original = Number(row.product_uom_qty || 0) * Number(row.price_unit || 0); const fixed = row.managed_discount_mode === "fixed" ? Number(row.managed_discount_fixed || 0) : 0; return <article key={String(row.id || `new-${index}`)}><div className="toova-sale-line-copy"><strong>{label(row.product_id) || "Produk belum dipilih"}</strong><span>{String(row.name || "Deskripsi akan terisi dari produk.")}</span><small>{Number(row.product_uom_qty || 0).toLocaleString("id-ID")} {label(row.product_uom)} × {money("price_unit", row)}</small></div><div className="toova-sale-line-subtotal">{discount > 0 && <><del>{money("price_subtotal", row, original)}</del><i>{fixed > 0 ? <>−{money("price_subtotal", row, fixed)}</> : <>−{discount.toLocaleString("id-ID", { maximumFractionDigits: 2 })}%</>}</i></>}<strong>{money("price_subtotal", row)}</strong></div><div className="managed-relation-card-actions"><button type="button" onClick={() => edit(index)} aria-label="Edit item"><Pencil/></button><button type="button" onClick={() => remove(index)} aria-label="Hapus item"><Trash2/></button></div></article>; })}
      {!rows.length && <div className="managed-relation-card-empty">Belum ada produk atau layanan.</div>}
    </div>
    <button type="button" className="workspace-relation-add" onClick={add}><Plus/>Tambah produk atau layanan</button>
    {open !== undefined && draft && createPortal(<div className="managed-relation-editor-backdrop" role="presentation"><section className="managed-relation-editor toova-sale-line-drawer" role="dialog" aria-modal="true"><header><div><h3>{draft.product_id ? "Edit item" : "Tambah item"}</h3><p>Pilih variant. Odoo mengisi deskripsi, satuan, pajak, dan harga.</p></div><button type="button" onClick={close} aria-label="Tutup"><X/></button></header><main>
      {control("product_id", true)}
      {Boolean(draft.product_id) && <>{control("name", true)}{control("product_uom_qty")}{control("product_uom")}{control("price_unit")}{control("managed_discount_mode")}{draft.managed_discount_mode === "fixed" ? control("managed_discount_fixed") : control("discount")}{control("tax_id", true)}</>}
    </main><footer><Button type="button" variant="ghost" onClick={close}>Batal</Button><Button type="button" onClick={save} disabled={!draft.product_id}>Simpan item</Button></footer></section></div>, document.body)}
  </div>;
}
