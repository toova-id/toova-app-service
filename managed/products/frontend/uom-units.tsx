import { Pencil, Plus, Ruler, Trash2, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@luma/components/ui/button";
import { Input } from "@luma/components/ui/input";
import { Switch } from "@luma/components/ui/switch";
import type { FieldSchema } from "@luma/views/types";

type Row = Record<string, unknown>;
type Props = { field: FieldSchema; value: unknown; onChange: (value: unknown) => void };
const number = (value: unknown) => Number(value || 0);

export function UomUnitsEditor({ field, value, onChange }: Props) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const active = rows.filter((row) => row.active !== false);
  const base = active.find((row) => row.uom_type === "reference" || Math.abs(number(row.managed_base_quantity) - 1) < 1e-12);
  const [open, setOpen] = useState<number>();
  const [draft, setDraft] = useState<Row>();
  const add = () => { setOpen(rows.length); setDraft({ name: "", managed_base_quantity: active.length ? 0 : 1, rounding: 0.01, active: true }); };
  const edit = (index: number) => { setOpen(index); setDraft({ ...rows[index] }); };
  const close = () => { setOpen(undefined); setDraft(undefined); };
  const save = () => { if (open === undefined || !draft) return; const next = open < rows.length ? rows.map((row, index) => index === open ? draft : row) : [...rows, draft]; onChange(next); close(); };
  const archive = (index: number) => {
    const row = rows[index];
    if (row.uom_type === "reference" || Math.abs(number(row.managed_base_quantity) - 1) < 1e-12) return;
    onChange(rows.map((item, position) => position === index ? { ...item, active: false } : item));
  };
  const locked = Boolean(draft?.managed_conversion_locked);
  const isBase = Boolean(draft && (draft.uom_type === "reference" || Math.abs(number(draft.managed_base_quantity) - 1) < 1e-12));
  const baseName = String(base?.name || "satuan dasar");
  return <div className="luma-uom-units">
    <div className="luma-uom-unit-list">{active.map((row) => { const index = rows.indexOf(row); const rowBase = row.uom_type === "reference" || Math.abs(number(row.managed_base_quantity) - 1) < 1e-12; return <article key={String(row.id || `new-${index}`)}><div className="luma-uom-unit-icon"><Ruler/></div><div><strong>{String(row.name || "Satuan baru")}{rowBase && <i>Satuan dasar</i>}</strong><span>{rowBase ? `1 ${String(row.name || "unit")} menjadi acuan konversi` : `1 ${String(row.name || "unit")} = ${number(row.managed_base_quantity).toLocaleString("id-ID", { maximumFractionDigits: 12 })} ${baseName}`} · minimum {number(row.rounding).toLocaleString("id-ID", { maximumFractionDigits: 12 })}{number(row.managed_usage_count) ? ` · ${number(row.managed_usage_count)} produk` : ""}</span></div><div className="managed-relation-card-actions"><button type="button" onClick={() => edit(index)} aria-label={`Edit ${String(row.name || "satuan")}`}><Pencil/></button>{!rowBase && <button type="button" onClick={() => archive(index)} aria-label={`Arsipkan ${String(row.name || "satuan")}`}><Trash2/></button>}</div></article>; })}{!active.length && <div className="managed-relation-card-empty">Belum ada satuan. Tambahkan satuan dasar terlebih dahulu.</div>}</div>
    <button type="button" className="workspace-relation-add" onClick={add}><Plus/>{active.length ? "Tambah satuan konversi" : "Tambah satuan dasar"}</button>
    {open !== undefined && draft && <div className="managed-relation-editor-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><section className="managed-relation-editor luma-uom-unit-drawer" role="dialog" aria-modal="true"><header><div><h3>{isBase ? "Satuan dasar" : "Satuan konversi"}</h3><p>{active.length && !isBase ? `Masukkan nilai dengan bentuk 1 satuan ini = jumlah ${baseName}.` : "Satuan dasar menjadi acuan seluruh konversi pada kelompok ini."}</p></div><button type="button" onClick={close} aria-label="Tutup"><X/></button></header><main>
      <label className="wide"><span>Nama satuan<b>*</b></span><Input value={String(draft.name || "")} placeholder="Contoh: ml, kg, lusin" onChange={(event) => setDraft({ ...draft, name: event.target.value })}/></label>
      <label className="wide"><span>Nilai dalam {baseName}<b>*</b></span><div className="luma-uom-equation"><b>1 {String(draft.name || "satuan")}</b><span>=</span><Input type="number" min="0" step="any" disabled={isBase || locked} value={String(draft.managed_base_quantity ?? "")} onChange={(event) => setDraft({ ...draft, managed_base_quantity: event.target.value === "" ? 0 : Number(event.target.value) })}/><b>{baseName}</b></div>{locked && <small>Konversi terkunci karena satuan sudah dipakai transaksi.</small>}</label>
      <label><span>Kuantitas minimum<b>*</b></span><Input type="number" min="0" step="any" disabled={locked} value={String(draft.rounding ?? "")} onChange={(event) => setDraft({ ...draft, rounding: event.target.value === "" ? 0 : Number(event.target.value) })}/></label>
      <label><span>Aktif</span><Switch checked={draft.active !== false} onChange={(event) => setDraft({ ...draft, active: event.target.checked })}/></label>
    </main><footer><Button type="button" variant="ghost" onClick={close}>Batal</Button><Button type="button" onClick={save} disabled={!String(draft.name || "").trim() || number(draft.managed_base_quantity) <= 0 || number(draft.rounding) <= 0}>Simpan satuan</Button></footer></section></div>}
  </div>;
}

export function UomUnitsValue({ value }: { value: unknown }) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const active = rows.filter((row) => row.active !== false);
  const base = active.find((row) => row.uom_type === "reference");
  return <div className="luma-uom-read">{active.map((row, index) => <span key={String(row.id || index)}><strong>{String(row.name || "Satuan")}</strong><i>{row === base ? "Satuan dasar" : `1 = ${number(row.managed_base_quantity).toLocaleString("id-ID", { maximumFractionDigits: 12 })} ${String(base?.name || "dasar")}`}</i></span>)}{!active.length && <span>Belum ada satuan</span>}</div>;
}
