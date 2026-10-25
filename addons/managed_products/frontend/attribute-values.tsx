import { Plus, Trash2 } from "lucide-react";
import { useEffect, useRef } from "react";
import { Checkbox } from "@luma/components/ui/checkbox";
import { Input } from "@luma/components/ui/input";
import type { FieldSchema } from "@luma/views/types";

type Row = Record<string, unknown>;
type Props = { actionId: number; field: FieldSchema; value: unknown; onChange: (value: unknown) => void; parentValues?: Row; advanced?: boolean };

export function AttributeValuesEditor({ value, onChange, parentValues, advanced = false }: Props) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const inputs = useRef(new Map<number, HTMLInputElement>());
  const active = rows.filter((row) => row.active !== false);
  const colorMode = parentValues?.display_type === "color";
  useEffect(() => { if (!rows.length) onChange([{ name: "", html_color: false, is_custom: false, sequence: 0, active: true }]); }, [rows.length, onChange]);
  const update = (index: number, name: string, next: unknown) => onChange(rows.map((row, position) => position === index ? { ...row, [name]: next } : row));
  const add = (afterIndex?: number) => {
    const position = afterIndex === undefined ? rows.length : afterIndex + 1;
    const next = [...rows];
    next.splice(position, 0, { name: "", html_color: colorMode ? "#000000" : false, is_custom: false, sequence: position * 10, active: true });
    onChange(next.map((row, index) => ({ ...row, sequence: index * 10 })));
    requestAnimationFrame(() => inputs.current.get(position)?.focus());
  };
  const remove = (index: number) => {
    onChange(rows[index]?.id ? rows.map((row, position) => position === index ? { ...row, active: false } : row) : rows.filter((_, position) => position !== index));
    requestAnimationFrame(() => inputs.current.get(Math.max(0, index - 1))?.focus());
  };
  const names = active.map((row) => String(row.name || "").trim().toLocaleLowerCase("id-ID"));
  return <div className={`luma-attribute-values ${colorMode ? "color-mode" : ""} ${advanced ? "advanced" : ""}`}>
    <div className="luma-attribute-values-head"><span>Nama nilai</span>{colorMode && <span>Warna</span>}{advanced && <span>Nilai bebas</span>}<span/></div>
    {active.map((row, activeIndex) => { const index = rows.indexOf(row); const duplicate = Boolean(names[activeIndex]) && names.indexOf(names[activeIndex]) !== activeIndex; return <div className={`luma-attribute-value-row ${duplicate ? "invalid" : ""}`} key={String(row.id || `new-${index}`)}>
      <div><Input ref={(node) => { if (node) inputs.current.set(index, node); else inputs.current.delete(index); }} value={String(row.name || "")} placeholder="Contoh: 250 ml, Merah, XL" aria-invalid={duplicate} onChange={(event) => update(index, "name", event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); add(index); } else if (event.key === "Backspace" && !row.name && active.length > 1) { event.preventDefault(); remove(index); } }}/>{duplicate && <small>Nilai sudah ada</small>}</div>
      {colorMode && <label className="luma-attribute-color-input"><input type="color" value={String(row.html_color || "#000000")} aria-label={`Warna ${String(row.name || activeIndex + 1)}`} onChange={(event) => update(index, "html_color", event.target.value)}/><span>{String(row.html_color || "#000000")}</span></label>}
      {advanced && <label className="luma-attribute-custom"><Checkbox checked={Boolean(row.is_custom)} onCheckedChange={(checked) => update(index, "is_custom", checked === true)}/><span>Izinkan teks bebas</span></label>}
      <button type="button" aria-label="Hapus nilai" onClick={() => remove(index)}><Trash2/></button>
    </div>; })}
    {!active.length && <div className="luma-variant-empty"><strong>Belum ada nilai</strong><span>Tambahkan pilihan seperti 250 ml, 500 ml, atau 1 L.</span></div>}
    <button type="button" className="workspace-relation-add" onClick={() => add()}><Plus/>Tambah nilai</button>
    <p className="luma-attribute-keyboard-hint">Tekan Enter untuk langsung menambah baris berikutnya.</p>
  </div>;
}

export function AttributeValuesValue({ value }: { value: unknown }) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const active = rows.filter((row) => row.active !== false);
  return <div className="luma-attribute-summary">{active.map((row, index) => <span key={String(row.id || index)}>{Boolean(row.html_color) && <i className="luma-attribute-color" style={{ backgroundColor: String(row.html_color) }}/>}<strong>{String(row.name || "Nilai baru")}</strong></span>)}{!active.length && <i>Belum ada nilai</i>}</div>;
}
