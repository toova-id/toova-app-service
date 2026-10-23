import { Plus, Trash2 } from "lucide-react";
import { useEffect, useId, useRef, useState, type ChangeEvent } from "react";
import { api } from "@/lib/api";
import type { FieldSchema } from "./types";

type Value = unknown;
type DisplayProps = { field: FieldSchema; value: Value; record: Record<string, unknown> };
type EditorProps = { actionId: number; field: FieldSchema; value: Value; onChange: (value: Value) => void };
type Renderer = (props: DisplayProps) => JSX.Element;
type Editor = (props: EditorProps) => JSX.Element;
const display: Record<string, Renderer> = {};
const editors: Record<string, Editor> = {};
const text = (value: Value) => value === false || value == null ? "—" : String(value);
const localDateTime = (value: Value) => value ? String(value).replace(" ", "T").slice(0, 16) : "";

function TagsEditor({ actionId, field, value, onChange }: EditorProps) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<{ id: number; label: string }[]>([]);
  const selected = Array.isArray(value) ? value : [];
  useEffect(() => { const params = new URLSearchParams({ q: query, ...(field.parent ? { parent: field.parent } : {}) }); const timeout = setTimeout(() => api<{ items: { id: number; label: string }[] }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}?${params}`).then((response) => setItems(response.items)).catch(() => setItems([])), 120); return () => clearTimeout(timeout); }, [actionId, field.name, field.parent, query]);
  const selectedIds = new Set(selected.map((item) => Array.isArray(item) ? item[0] : item));
  return <div className="workspace-tags-editor"><div>{selected.map((item) => { const id = Array.isArray(item) ? item[0] : item; const label = Array.isArray(item) ? item[1] : String(item); return <span key={String(id)}>{label}<button type="button" onClick={() => onChange(selected.filter((current) => (Array.isArray(current) ? current[0] : current) !== id))}>×</button></span>; })}</div><input value={query} placeholder="Tambah..." onChange={(event) => setQuery(event.target.value)}/>{query && <ul>{items.filter((item) => !selectedIds.has(item.id)).map((item) => <li key={item.id}><button type="button" onClick={() => { onChange([...selected, [item.id, item.label]]); setQuery(""); }}>{item.label}</button></li>)}</ul>}</div>;
}

export function registerFieldRenderer(type: string, renderer: Renderer) { display[type] = renderer; }
export function registerFieldEditor(type: string, editor: Editor) { editors[type] = editor; }

registerFieldRenderer("default", ({ value }) => <>{text(value)}</>);
registerFieldRenderer("many2one", ({ value }) => <>{Array.isArray(value) ? text(value[1]) : text(value)}</>);
function RelationTable({ actionId, field, value, onChange, editing }: EditorProps & { editing: boolean }) {
  const rows = Array.isArray(value) ? value as Record<string, unknown>[] : [];
  const columns = field.relationView?.columns || [];
  if (!field.relationView) return <span className="workspace-tags">{rows.length ? `${rows.length} item` : "—"}</span>;
  const update = (index: number, name: string, nextValue: unknown) => onChange(rows.map((row, rowIndex) => rowIndex === index ? { ...row, [name]: nextValue } : row));
  return <div className="workspace-relation"><div className="overflow-x-auto"><table><thead><tr>{columns.map((column) => <th key={column.name}>{column.label}</th>)}{editing && <th/>}</tr></thead><tbody>{rows.map((row, index) => <tr key={String(row.id || `new-${index}`)}>{columns.map((column) => <td key={column.name}>{editing && field.relationView?.editable ? <FieldEditor actionId={actionId} field={column} value={row[column.name]} onChange={(nextValue) => update(index, column.name, nextValue)}/> : <FieldValue field={column} value={row[column.name]} record={row}/>}</td>)}{editing && <td className="workspace-relation-delete"><button type="button" onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}><Trash2/></button></td>}</tr>)}</tbody></table></div>{editing && field.relationView.editable && <button type="button" className="workspace-relation-add" onClick={() => onChange([...rows, {}])}><Plus/>Tambah baris</button>}{!rows.length && !editing && <span className="workspace-relation-empty">Belum ada baris</span>}</div>;
}
registerFieldRenderer("many2many", (props) => <RelationTable actionId={0} {...props} onChange={() => undefined} editing={false}/>);
registerFieldRenderer("one2many", display.many2many);
registerFieldRenderer("boolean", ({ value }) => <span className={value ? "workspace-boolean-on" : "workspace-boolean-off"}>{value ? "Ya" : "Tidak"}</span>);
registerFieldRenderer("boolean_toggle", display.boolean);
registerFieldRenderer("boolean_favorite", display.boolean);
registerFieldRenderer("selection", ({ field, value }) => <>{field.selection?.find(([key]) => key === value)?.[1] ?? text(value)}</>);
registerFieldRenderer("badge", ({ field, value }) => <span className="workspace-badge">{field.selection?.find(([key]) => key === value)?.[1] ?? text(value)}</span>);
registerFieldRenderer("statusbar", display.badge);
registerFieldRenderer("date", ({ value }) => <>{value ? new Date(`${value}T00:00:00`).toLocaleDateString("id-ID") : "—"}</>);
registerFieldRenderer("datetime", ({ value }) => <>{value ? new Date(String(value).replace(" ", "T") + "Z").toLocaleString("id-ID") : "—"}</>);
registerFieldRenderer("float_time", ({ value }) => { const hours = Number(value || 0); return <>{`${Math.floor(hours)}:${String(Math.round(hours % 1 * 60)).padStart(2, "0")}`}</>; });
registerFieldRenderer("percentage", ({ value }) => <>{`${Number(value || 0).toLocaleString("id-ID")}%`}</>);
registerFieldRenderer("progressbar", ({ value }) => <span className="workspace-progress"><i style={{ width: `${Math.max(0, Math.min(100, Number(value || 0)))}%` }}/></span>);
registerFieldRenderer("image", ({ value }) => value ? <img className="h-8 w-8 rounded object-cover" src={`data:image/png;base64,${value}`} alt=""/> : <>—</>);
registerFieldRenderer("binary", ({ field, value }) => field.widget === "image" && value ? <img className="h-8 w-8 rounded object-cover" src={`data:image/png;base64,${value}`} alt=""/> : <>{value ? "Berkas" : "—"}</>);
registerFieldRenderer("html", ({ value }) => <span className="line-clamp-2" dangerouslySetInnerHTML={{ __html: String(value || "") }}/>)
registerFieldRenderer("priority", ({ value }) => <span className="workspace-priority-read">{Number(value || 0) ? "★".repeat(Number(value)) : "☆"}</span>);
registerFieldRenderer("color", ({ value }) => <span className="workspace-color" style={{ backgroundColor: `hsl(${Number(value || 0) * 30} 65% 55%)` }}/>)
registerFieldRenderer("monetary", ({ field, value, record }) => {
  const currency = field.currency_field && record[field.currency_field];
  const currencyCode = Array.isArray(currency) && /^[A-Z]{3}$/.test(String(currency[1])) ? String(currency[1]) : "IDR";
  try { return <>{new Intl.NumberFormat("id-ID", { style: "currency", currency: currencyCode, maximumFractionDigits: 0 }).format(Number(value || 0))}</>; }
  catch { return <>{text(value)}</>; }
});

const input = (type = "text"): Editor => ({ field, value, onChange }) => <input type={type} placeholder={field.placeholder} value={value == null || value === false ? "" : String(value)} onChange={(event) => onChange(event.target.value)}/>;
editors.default = input();
editors.char = input();
editors.phone = input("tel");
editors.email = input("email");
editors.url = input("url");
editors.text = ({ field, value, onChange }) => <textarea placeholder={field.placeholder} value={value == null || value === false ? "" : String(value)} onChange={(event) => onChange(event.target.value)}/>;
editors.html = editors.text;
editors.integer = ({ field, value, onChange }) => <input type="number" placeholder={field.placeholder} value={value == null || value === false ? "" : String(value)} onChange={(event) => onChange(event.target.value === "" ? false : Number(event.target.value))}/>;
editors.float = editors.integer;
editors.monetary = editors.integer;
editors.percentage = editors.integer;
editors.float_time = editors.integer;
editors.boolean = ({ value, onChange }) => <label className="workspace-switch"><input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)}/><span/></label>;
editors.boolean_toggle = editors.boolean;
editors.boolean_favorite = editors.boolean;
editors.selection = ({ field, value, onChange }) => <select value={String(value ?? "")} onChange={(event: ChangeEvent<HTMLSelectElement>) => onChange(event.target.value || false)}><option value="">Pilih...</option>{field.selection?.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select>;
editors.radio = ({ field, value, onChange }) => <div className="workspace-radio-group">{field.selection?.map(([key, label]) => <label key={key}><input type="radio" checked={value === key} onChange={() => onChange(key)}/><span>{label}</span></label>)}</div>;
editors.date = ({ field, value, onChange }) => <input type="date" placeholder={field.placeholder} value={value ? String(value).slice(0, 10) : ""} onChange={(event) => onChange(event.target.value || false)}/>;
editors.datetime = ({ field, value, onChange }) => <input type="datetime-local" placeholder={field.placeholder} value={localDateTime(value)} onChange={(event) => onChange(event.target.value ? event.target.value.replace("T", " ") + ":00" : false)}/>;
editors.binary = ({ field, onChange }) => <label className="workspace-file-input"><input type="file" accept={field.accept || (field.widget === "image" ? "image/*" : undefined)} onChange={(event) => { const file = event.target.files?.[0]; if (!file) return onChange(false); const reader = new FileReader(); reader.onload = () => onChange(String(reader.result).split(",", 2)[1] || false); reader.readAsDataURL(file); }}/><span>Pilih berkas</span></label>;
editors.image = editors.binary;
editors.one2many = (props) => <RelationTable {...props} editing/>;
editors.many2many = (props) => props.field.relationView ? <RelationTable {...props} editing/> : <TagsEditor {...props}/>;
editors.many2many_tags = (props) => <TagsEditor {...props}/>;
editors.priority = ({ field, value, onChange }) => <div className="workspace-priority">{(field.selection || [["0", "Normal"], ["1", "Penting"], ["2", "Sangat penting"]]).map(([key, label]) => <button type="button" key={key} className={String(value || "0") >= key && key !== "0" ? "active" : ""} title={label} onClick={() => onChange(key)}>★</button>)}</div>;
editors.color = ({ value, onChange }) => <input type="number" min="0" max="11" value={Number(value || 0)} onChange={(event) => onChange(Number(event.target.value))}/>;
editors.many2one = function RelationEditor({ actionId, field, value, onChange }) {
  const listId = useId();
  const controller = useRef<AbortController>();
  const [items, setItems] = useState<{ id: number; label: string }[]>([]);
  const [query, setQuery] = useState(Array.isArray(value) ? String(value[1]) : "");
  const selectedLabel = Array.isArray(value) ? String(value[1]) : "";
  useEffect(() => { if (selectedLabel && !query) setQuery(selectedLabel); }, [selectedLabel]);
  useEffect(() => {
    controller.current?.abort();
    controller.current = new AbortController();
    const params = new URLSearchParams({ q: query, ...(field.parent ? { parent: field.parent } : {}) });
    const timeout = setTimeout(() => api<{ items: { id: number; label: string }[] }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}?${params}`, { signal: controller.current?.signal }).then((response) => setItems(response.items)).catch((error) => { if (error.name !== "AbortError") setItems([]); }), 120);
    return () => { clearTimeout(timeout); controller.current?.abort(); };
  }, [actionId, field.name, field.parent, query]);
  return <><input list={listId} value={query} placeholder={field.placeholder || "Cari..."} onFocus={() => setQuery((current) => current)} onChange={(event) => { const next = event.target.value; setQuery(next); const selected = items.find((item) => item.label === next); onChange(selected ? [selected.id, selected.label] : false); }}/><datalist id={listId}>{items.map((item) => <option key={item.id} value={item.label}/>)}</datalist></>;
};
editors.res_partner_many2one = editors.many2one;
editors.many2one_avatar_user = editors.many2one;
editors.many2one_avatar_employee = editors.many2one;

export function FieldValue(props: DisplayProps) { const Renderer = display[props.field.widget || props.field.type] || display[props.field.type] || display.default; return <Renderer {...props}/>; }
export function FieldEditor(props: EditorProps) { const Editor = editors[props.field.widget || props.field.type] || editors[props.field.type] || editors.default; return <Editor {...props}/>; }
