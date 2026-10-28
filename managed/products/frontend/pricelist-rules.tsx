import { Pencil, Plus, Tags, Trash2, X } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "@luma/components/ui/button";
import { FieldEditor } from "@luma/views/field-registry";
import { apiMutation } from "@luma/lib/api";
import type { FieldSchema } from "@luma/views/types";

type Props = { actionId: number; field: FieldSchema; value: unknown; parentValues?: Record<string, unknown>; onChange: (value: unknown) => void };
type Row = Record<string, unknown>;
const relation = (value: unknown) => Array.isArray(value) ? String(value[1]) : "";
const date = (value: unknown) => value ? new Date(String(value).replace(" ", "T") + "Z").toLocaleDateString("id-ID") : "";

export function PricelistRulesEditor({ actionId, field, value, parentValues, onChange }: Props) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const columns = field.relationView?.columns || [];
  const byName = Object.fromEntries(columns.map((column) => [column.name, column])) as Record<string, FieldSchema>;
  const [open, setOpen] = useState<number>();
  const [draft, setDraft] = useState<Row>();
  const [advanced, setAdvanced] = useState(false);
  const request = useRef(0);
  const active = rows.filter((row) => row.active !== false);
  const close = () => { setOpen(undefined); setDraft(undefined); setAdvanced(false); };
  const add = () => { setOpen(rows.length); setDraft({ applied_on: "3_global", compute_price: "fixed", base: "list_price", min_quantity: 0, fixed_price: 0 }); };
  const edit = (index: number) => { const row = rows[index]; setOpen(index); setDraft({ ...row }); setAdvanced(row.compute_price === "formula"); };
  const archive = (index: number) => onChange(rows.map((row, position) => position === index ? { ...row, active: false } : row));
  const save = () => { if (open === undefined || !draft) return; onChange(open < rows.length ? rows.map((row, index) => index === open ? draft : row) : [...rows, draft]); close(); };
  const update = async (name: string, nextValue: unknown) => {
    let next = { ...(draft || {}), [name]: nextValue };
    if (name === "applied_on") next = { ...next, categ_id: false, product_tmpl_id: false, product_id: false };
    if (name === "product_tmpl_id") next.product_id = false;
    setDraft(next);
    if (name === "applied_on" || field.relationView?.onchange?.[name] !== "1") return;
    const current = ++request.current;
    try {
      const result = await apiMutation<{ values: Row }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}/onchange`, "POST", { values: next, parentValues: parentValues || {}, field: name });
      if (current === request.current) setDraft((value) => ({ ...(value || {}), ...result.values, applied_on: next.applied_on }));
    } catch { /* Server validates again when parent saves. */ }
  };
  const control = (name: string, wide = false) => { const meta = byName[name]; if (!meta || !draft) return null; return <label className={wide ? "wide" : undefined}><span>{meta.label}{meta.required && <b>*</b>}</span><FieldEditor actionId={actionId} field={meta} value={draft[name]} parentValues={{ ...draft, __parent_id: parentValues?.id }} onChange={(value) => update(name, value)}/></label>; };
  const scope = (row: Row) => row.applied_on === "2_product_category" ? relation(row.categ_id) : row.applied_on === "1_product" ? relation(row.product_tmpl_id) : row.applied_on === "0_product_variant" ? relation(row.product_id) : "Semua produk";
  const price = (row: Row) => row.compute_price === "percentage" ? `${Number(row.percent_price || 0).toLocaleString("id-ID")}% diskon` : row.compute_price === "formula" ? "Formula lanjutan" : Number(row.fixed_price || 0).toLocaleString("id-ID");
  const targetReady = !draft || draft.applied_on === "3_global" || draft.applied_on === "2_product_category" && Boolean(draft.categ_id) || draft.applied_on === "1_product" && Boolean(draft.product_tmpl_id) || draft.applied_on === "0_product_variant" && Boolean(draft.product_tmpl_id) && Boolean(draft.product_id);
  return <div className="luma-pricelist-rules">
    <div className="luma-pricelist-rule-list">{active.map((row) => { const index = rows.indexOf(row); const period = [date(row.date_start), date(row.date_end)].filter(Boolean).join(" – "); return <article key={String(row.id || `new-${index}`)}><div className="luma-pricelist-rule-icon"><Tags/></div><div><strong>{scope(row)}</strong><span>{price(row)} · minimum {Number(row.min_quantity || 0).toLocaleString("id-ID")}{period ? ` · ${period}` : ""}</span></div><div className="managed-relation-card-actions"><button type="button" onClick={() => edit(index)} aria-label={`Edit aturan ${scope(row)}`}><Pencil/></button><button type="button" onClick={() => archive(index)} aria-label={`Hapus aturan ${scope(row)}`}><Trash2/></button></div></article>; })}{!active.length && <div className="managed-relation-card-empty">Belum ada aturan. Tanpa aturan, harga jual produk tetap digunakan.</div>}</div>
    <button type="button" className="workspace-relation-add" onClick={add}><Plus/>Tambah aturan harga</button>
    {open !== undefined && draft && <div className="managed-relation-editor-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><section className="managed-relation-editor luma-pricelist-rule-drawer" role="dialog" aria-modal="true"><header><div><h3>Aturan harga</h3><p>Tentukan produk yang menerima harga, minimum kuantitas, dan periode berlaku.</p></div><button type="button" onClick={close} aria-label="Tutup"><X/></button></header><main>
      {control("applied_on", true)}
      {draft.applied_on === "2_product_category" && control("categ_id", true)}
      {draft.applied_on === "1_product" && control("product_tmpl_id", true)}
      {draft.applied_on === "0_product_variant" && <>{control("product_tmpl_id", true)}{draft.product_tmpl_id ? control("product_id", true) : <p className="luma-pricelist-target-hint wide">Pilih produk terlebih dahulu agar daftar variant tersedia.</p>}</>}
      {control("compute_price", true)}
      {draft.compute_price === "fixed" && control("fixed_price", true)}
      {draft.compute_price === "percentage" && control("percent_price", true)}
      {control("min_quantity")}{control("date_start")}{control("date_end")}
      {draft.compute_price === "formula" && <><button type="button" className="luma-pricelist-advanced-toggle wide" onClick={() => setAdvanced((value) => !value)}>{advanced ? "Sembunyikan formula" : "Tampilkan formula lanjutan"}</button>{advanced && <>{control("base")}{draft.base === "pricelist" && control("base_pricelist_id")}{control("price_discount")}{control("price_surcharge")}{control("price_round")}{control("price_min_margin")}{control("price_max_margin")}</>}</>}
    </main><footer><Button type="button" variant="ghost" onClick={close}>Batal</Button><Button type="button" onClick={save} disabled={!targetReady}>Simpan aturan</Button></footer></section></div>}
  </div>;
}

export function PricelistRulesValue({ value }: { value: unknown }) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const count = rows.filter((row) => row.active !== false).length;
  return <span>{count ? `${count} aturan harga` : "Belum ada aturan"}</span>;
}
