import { GripVertical, Plus, Trash2 } from "lucide-react";
import { FieldEditor } from "@luma/views/field-registry";
import type { FieldSchema } from "@luma/views/types";

type Row = Record<string, unknown>;
type Props = { actionId: number; field: FieldSchema; value: unknown; onChange: (value: unknown) => void; parentValues?: Row };

export function AttributeValuesEditor({ actionId, field, value, onChange, parentValues }: Props) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  const columns = Object.fromEntries((field.relationView?.columns || []).map((column) => [column.name, column])) as Record<string, FieldSchema>;
  const active = rows.filter((row) => row.active !== false);
  const update = (index: number, name: string, next: unknown) => onChange(rows.map((row, position) => position === index ? { ...row, [name]: next } : row));
  const remove = (index: number) => onChange(rows[index]?.id ? rows.map((row, position) => position === index ? { ...row, active: false } : row) : rows.filter((_, position) => position !== index));
  return <div className="luma-attribute-values"><div className="luma-attribute-values-head"><span>Nilai</span><span>Warna HTML</span><span>Custom</span><span/></div>{active.map((row) => { const index = rows.indexOf(row); return <div className="luma-attribute-value-row" key={String(row.id || `new-${index}`)}><GripVertical/><FieldEditor actionId={actionId} field={columns.name} value={row.name} parentValues={parentValues} onChange={(next) => update(index, "name", next)}/><FieldEditor actionId={actionId} field={columns.html_color} value={row.html_color} parentValues={parentValues} onChange={(next) => update(index, "html_color", next)}/><FieldEditor actionId={actionId} field={columns.is_custom} value={row.is_custom} parentValues={parentValues} onChange={(next) => update(index, "is_custom", next)}/><button type="button" aria-label="Hapus nilai" onClick={() => remove(index)}><Trash2/></button></div>; })}{!active.length && <div className="luma-variant-empty">Belum ada nilai atribut.</div>}<button type="button" className="workspace-relation-add" onClick={() => onChange([...rows, { name: "", html_color: false, is_custom: false, sequence: rows.length * 10, active: true }])}><Plus/>Tambah nilai</button></div>;
}

export function AttributeValuesValue({ value }: { value: unknown }) {
  const rows = Array.isArray(value) ? value as Row[] : [];
  return <div className="luma-attribute-summary">{rows.filter((row) => row.active !== false).map((row, index) => <span key={String(row.id || index)}>{Boolean(row.html_color) && <i className="luma-attribute-color" style={{ backgroundColor: String(row.html_color) }}/>}<strong>{String(row.name || "Nilai baru")}</strong></span>)}{!rows.length && <i>Belum ada nilai</i>}</div>;
}
