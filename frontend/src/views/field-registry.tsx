import { Check, Clipboard, Download, ExternalLink, FileText, Landmark, MapPin, Pencil, Plus, Trash2, Truck, Upload, UserRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, apiMutation } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Combobox } from "@/components/ui/combobox";
import { DatePicker } from "@/components/ui/date-picker";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { ImageUpload, imageSource } from "@/components/ui/image-upload";
import { Input } from "@/components/ui/input";
import { MultiSelect } from "@/components/ui/multi-select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { TimePicker } from "@/components/ui/time-picker";
import { Textarea } from "@/components/ui/textarea";
import type { FieldSchema } from "./types";

type Value = unknown;
type DisplayProps = { field: FieldSchema; value: Value; record: Record<string, unknown> };
type EditorProps = { actionId: number; field: FieldSchema; value: Value; onChange: (value: Value) => void; parentValues?: Record<string, unknown> };
type Renderer = (props: DisplayProps) => JSX.Element;
type Editor = (props: EditorProps) => JSX.Element;
const display: Record<string, Renderer> = {};
const editors: Record<string, Editor> = {};
const text = (value: Value) => value === false || value == null ? "—" : String(value);
const localDateTime = (value: Value) => value ? String(value).replace(" ", "T").slice(0, 16) : "";
const relationId = (item: unknown) => Array.isArray(item) ? Number(item[0]) : Number(item);
const relationLabel = (item: unknown) => Array.isArray(item) ? String(item[1]) : String(item);

function relationParams(field: FieldSchema, query = "", parentValues?: Record<string, unknown>) { return new URLSearchParams({ q: query, ...(field.parent ? { parent: field.parent } : {}), ...(parentValues ? { values: JSON.stringify(parentValues) } : {}), ...(parentValues?.id ? { recordId: String(parentValues.id) } : {}) }); }

function TagsEditor({ actionId, field, value, onChange, parentValues }: EditorProps) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<{ id: number; label: string }[]>([]);
  const selected = Array.isArray(value) ? value : [];
  useEffect(() => { const params = relationParams(field, query, parentValues); const timeout = setTimeout(() => api<{ items: { id: number; label: string }[] }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}?${params}`).then((response) => setItems(response.items)).catch(() => setItems([])), 120); return () => clearTimeout(timeout); }, [actionId, field.name, field.parent, parentValues, query]);
  const selectedIds = new Set(selected.map((item) => Array.isArray(item) ? item[0] : item));
  const options = [...selected.map((item) => ({ value: relationId(item), label: relationLabel(item) })), ...items.filter((item) => !selectedIds.has(item.id)).map((item) => ({ value: item.id, label: item.label }))];
  return <MultiSelect options={options} value={selected.map((item) => ({ value: relationId(item), label: relationLabel(item) }))} onSearch={setQuery} onChange={(next) => onChange(next.map((item) => [Number(item.value), item.label]))} placeholder="Pilih..."/>;
}

function JsonEditor({ field, value, onChange }: EditorProps) {
  const [source, setSource] = useState(() => JSON.stringify(value || (field.type === "json" ? {} : []), null, 2));
  const [invalid, setInvalid] = useState(false);
  useEffect(() => setSource(JSON.stringify(value || (field.type === "json" ? {} : []), null, 2)), [value, field.type]);
  return <div className="workspace-json-editor"><Textarea value={source} aria-invalid={invalid} onChange={(event) => { const next = event.target.value; setSource(next); try { onChange(JSON.parse(next)); setInvalid(false); } catch { setInvalid(true); } }}/>{invalid && <span>JSON tidak valid</span>}</div>;
}

function RelationCheckboxes({ actionId, field, value, onChange }: EditorProps) {
  const [items, setItems] = useState<{ id: number; label: string }[]>([]);
  const selected = Array.isArray(value) ? value : [];
  useEffect(() => { const controller = new AbortController(); api<{ items: { id: number; label: string }[] }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}?${relationParams(field)}`, { signal: controller.signal }).then((result) => setItems(result.items)).catch((error) => { if (error.name !== "AbortError") setItems([]); }); return () => controller.abort(); }, [actionId, field.name, field.parent]);
  const ids = new Set(selected.map(relationId));
  return <div className="workspace-checkbox-group">{items.map((item) => <label key={item.id}><Checkbox checked={ids.has(item.id)} onCheckedChange={(checked) => onChange(checked === true ? [...selected, [item.id, item.label]] : selected.filter((entry) => relationId(entry) !== item.id))}/><span>{item.label}</span></label>)}</div>;
}

export function registerFieldRenderer(type: string, renderer: Renderer) { display[type] = renderer; }
export function registerFieldEditor(type: string, editor: Editor) { editors[type] = editor; }

registerFieldRenderer("default", ({ value }) => <>{text(value)}</>);
registerFieldRenderer("many2one", ({ value }) => <>{Array.isArray(value) ? text(value[1]) : text(value)}</>);
registerFieldRenderer("url", ({ value }) => value ? <a className="workspace-field-link" href={String(value)} target="_blank" rel="noreferrer">{String(value)}<ExternalLink/></a> : <>—</>);
registerFieldRenderer("email", ({ value }) => value ? <a className="workspace-field-link" href={`mailto:${String(value)}`}>{String(value)}</a> : <>—</>);
registerFieldRenderer("phone", ({ value }) => value ? <a className="workspace-field-link" href={`tel:${String(value)}`}>{String(value)}</a> : <>—</>);
registerFieldRenderer("CopyClipboardChar", ({ value }) => value ? <span className="workspace-copy-value">{String(value)}<button type="button" aria-label="Salin" onClick={() => navigator.clipboard.writeText(String(value))}><Clipboard/></button></span> : <>—</>);
function ManagedRelationCards({ actionId, field, value, onChange, editing, parentValues }: EditorProps & { editing: boolean }) {
  const rows = Array.isArray(value) ? value as Record<string, unknown>[] : [];
  const columns = field.relationView?.columns || [];
  const [open, setOpen] = useState<number>();
  const [draft, setDraft] = useState<Record<string, unknown>>();
  const draftSequence = useRef(0);
  const isAddress = field.widget === "managed_addresses";
  const isBank = field.widget === "managed_bank_accounts";
  const isSupplier = field.widget === "managed_supplier_prices";
  const productIdColumn = columns.find((column) => column.name === "product_id");
  const activeRows = rows.filter((row) => row.active !== false);
  const countryLabel = (row: Record<string, unknown>) => Array.isArray(row.country_id) ? String(row.country_id[1]) : "";
  const visibleColumn = (column: FieldSchema) => {
    if (isSupplier && column.name === "product_id" && !parentValues?.id) return false;
    if (!isAddress) return column.name !== "active";
    if (column.name === "active") return false;
    const indonesia = countryLabel(draft || {}) === "Indonesia";
    if (["indonesia_regency_id", "indonesia_district_id", "indonesia_village_id"].includes(column.name)) return indonesia;
    if (["city"].includes(column.name)) return !indonesia;
    return true;
  };
  const updateDraft = async (name: string, nextValue: unknown) => {
    const next = { ...(draft || {}), [name]: nextValue };
    if (isAddress && name === "country_id") {
      next.state_id = false;
      next.indonesia_regency_id = false;
      next.indonesia_district_id = false;
      next.indonesia_village_id = false;
      next.city = false;
      next.zip = false;
    }
    if (isAddress && name === "state_id") {
      next.indonesia_regency_id = false;
      next.indonesia_district_id = false;
      next.indonesia_village_id = false;
      next.city = false;
      next.zip = false;
    }
    if (isAddress && name === "is_default_billing" && nextValue === true) next.use_for_billing = true;
    if (isAddress && name === "is_default_shipping" && nextValue === true) next.use_for_shipping = true;
    setDraft(next);
    if (field.relationView?.onchange?.[name] !== "1") return;
    const request = ++draftSequence.current;
    try {
      const result = await apiMutation<{ values: Record<string, unknown> }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}/onchange`, "POST", { values: next, parentValues: parentValues || {}, field: name });
      if (request === draftSequence.current) setDraft((current) => ({ ...(current || {}), ...result.values }));
    } catch { /* Main form save remains server-validated. */ }
  };
  const edit = (index: number) => { setOpen(index); setDraft({ ...rows[index] }); };
  const add = () => { setOpen(rows.length); setDraft({ active: true, country_id: false, product_id: false }); };
  const close = () => { setOpen(undefined); setDraft(undefined); };
  const saveDraft = () => {
    if (open === undefined || !draft) return;
    let nextRows = open < rows.length ? rows.map((row, index) => index === open ? draft : row) : [...rows, draft];
    if (isAddress) {
      for (const fieldName of ["is_default_billing", "is_default_shipping"]) {
        if (draft[fieldName] === true) nextRows = nextRows.map((row, index) => index === open ? row : { ...row, [fieldName]: false });
      }
    }
    onChange(nextRows);
    close();
  };
  const archive = (index: number) => onChange(rows.map((row, rowIndex) => rowIndex === index ? { ...row, active: false, is_default_billing: false, is_default_shipping: false } : row));
  const label = (row: Record<string, unknown>) => String(Array.isArray(row.partner_id) ? row.partner_id[1] : row.label || row.name || row.bank_name || (isAddress ? "Alamat baru" : isBank ? "Rekening baru" : isSupplier ? "Harga vendor baru" : "Kontak baru"));
  const summary = (row: Record<string, unknown>) => isAddress
    ? [row.managed_address_text, Array.isArray(row.indonesia_village_id) ? row.indonesia_village_id[1] : false, Array.isArray(row.indonesia_district_id) ? row.indonesia_district_id[1] : false, Array.isArray(row.indonesia_regency_id) ? row.indonesia_regency_id[1] : row.city, Array.isArray(row.state_id) ? row.state_id[1] : false, row.zip, Array.isArray(row.country_id) ? row.country_id[1] : false].filter(Boolean).join(", ")
    : isBank ? [row.acc_number, row.acc_holder_name, Array.isArray(row.currency_id) ? row.currency_id[1] : false].filter(Boolean).join(" · ")
    : isSupplier ? [row.product_code, `${Number(row.min_qty || 0).toLocaleString("id-ID")}+`, `${Array.isArray(row.currency_id) ? row.currency_id[1] : ""} ${Number(row.price || 0).toLocaleString("id-ID")}`, `${Number(row.delay || 0)} hari`].filter(Boolean).join(" · ")
    : [row.function, row.email, row.mobile || row.phone].filter(Boolean).join(" · ");
  return <div className="managed-relation-cards">
    <div className="managed-relation-list">{activeRows.map((row) => { const index = rows.indexOf(row); return <article key={String(row.id || `new-${index}`)} className="managed-relation-card"><div className="managed-relation-card-icon">{isAddress ? <MapPin/> : isBank ? <Landmark/> : isSupplier ? <Truck/> : <UserRound/>}</div><div className="managed-relation-card-copy"><strong>{label(row)}</strong><span>{summary(row) || (isAddress ? "Alamat belum lengkap" : "Kontak belum lengkap")}</span>{isAddress && <div className="managed-address-badges">{Boolean(row.use_for_billing) && <i>Billing</i>}{Boolean(row.use_for_shipping) && <i>Shipping</i>}{Boolean(row.is_default_billing) && <i className="primary">Default billing</i>}{Boolean(row.is_default_shipping) && <i className="primary">Default shipping</i>}</div>}</div>{editing && <div className="managed-relation-card-actions"><button type="button" onClick={() => edit(index)} aria-label={`Edit ${label(row)}`}><Pencil/></button><button type="button" onClick={() => archive(index)} aria-label={`Arsipkan ${label(row)}`}><Trash2/></button></div>}</article>; })}{!activeRows.length && <div className="managed-relation-card-empty">{isAddress ? "Belum ada alamat khusus. Alamat utama masih menjadi fallback." : isBank ? "Belum ada rekening pembayaran." : isSupplier ? "Belum ada harga vendor. Cost default tetap dipakai." : "Belum ada PIC."}</div>}</div>
    {editing && <button type="button" className="workspace-relation-add" onClick={add}><Plus/>{isAddress ? "Tambah alamat" : isBank ? "Tambah rekening" : isSupplier ? "Tambah harga vendor" : "Tambah PIC"}</button>}
    {open !== undefined && draft && <div className="managed-relation-editor-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><section className="managed-relation-editor" role="dialog" aria-modal="true"><header><div><h3>{isAddress ? "Alamat bisnis" : isBank ? "Rekening pembayaran" : isSupplier ? "Harga vendor" : "Kontak/PIC"}</h3><p>{isAddress ? "Atur lokasi, penerima, penggunaan, dan default transaksi." : isBank ? "Simpan rekening resmi untuk pembayaran vendor." : isSupplier ? `Atur ${productIdColumn && parentValues?.id ? "scope variant, " : ""}kode vendor, minimum pembelian, harga, dan lead time.` : "Simpan orang yang dapat dihubungi pada organisasi ini."}</p></div><button type="button" onClick={close} aria-label="Tutup"><X/></button></header><main>{columns.filter(visibleColumn).map((column) => <label key={column.name} className={column.name === "managed_address_text" ? "wide" : undefined}><span>{column.label}{column.required && <b>*</b>}</span><FieldEditor actionId={actionId} field={column} value={draft[column.name]} parentValues={draft} onChange={(next) => updateDraft(column.name, next)}/></label>)}</main><footer><Button type="button" variant="ghost" onClick={close}>Batal</Button><Button type="button" onClick={saveDraft}>Simpan</Button></footer></section></div>}
  </div>;
}

function RelationTable({ actionId, field, value, onChange, editing, parentValues = {} }: EditorProps & { editing: boolean }) {
  const rows = Array.isArray(value) ? value as Record<string, unknown>[] : [];
  const columns = field.relationView?.columns || [];
  if (!field.relationView) return <span className="workspace-tags">{rows.length ? `${rows.length} item` : "—"}</span>;
  const sequence = useRef(0);
  const update = async (index: number, name: string, nextValue: unknown) => {
    const nextRows = rows.map((row, rowIndex) => rowIndex === index ? { ...row, [name]: nextValue } : row);
    onChange(nextRows);
    if (field.relationView?.onchange?.[name] !== "1") return;
    const request = ++sequence.current;
    try {
      const result = await apiMutation<{ values: Record<string, unknown> }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}/onchange`, "POST", { values: nextRows[index], parentValues, field: name });
      if (request === sequence.current) onChange(nextRows.map((row, rowIndex) => rowIndex === index ? { ...row, ...result.values } : row));
    } catch { /* Parent save still validates server-side. */ }
  };
  return <div className="workspace-relation"><div className="overflow-x-auto"><table><thead><tr>{columns.map((column) => <th key={column.name}>{column.label}</th>)}{editing && <th/>}</tr></thead><tbody>{rows.map((row, index) => <tr key={String(row.id || `new-${index}`)}>{columns.map((column) => <td key={column.name}>{editing && field.relationView?.editable ? <FieldEditor actionId={actionId} field={column} value={row[column.name]} onChange={(nextValue) => update(index, column.name, nextValue)}/> : <FieldValue field={column} value={row[column.name]} record={row}/>}</td>)}{editing && <td className="workspace-relation-delete"><button type="button" onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}><Trash2/></button></td>}</tr>)}</tbody></table></div>{editing && field.relationView.editable && <button type="button" className="workspace-relation-add" onClick={() => onChange([...rows, {}])}><Plus/>Tambah baris</button>}{!rows.length && !editing && <span className="workspace-relation-empty">Belum ada baris</span>}</div>;
}
registerFieldRenderer("many2many", (props) => <RelationTable actionId={0} {...props} onChange={() => undefined} editing={false}/>);
registerFieldRenderer("one2many", display.many2many);
registerFieldRenderer("managed_addresses", (props) => <ManagedRelationCards actionId={0} {...props} onChange={() => undefined} editing={false}/>);
registerFieldRenderer("managed_contacts", display.managed_addresses);
registerFieldRenderer("managed_bank_accounts", display.managed_addresses);
registerFieldRenderer("managed_supplier_prices", display.managed_addresses);
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
registerFieldRenderer("image", ({ value }) => { const source = imageSource(value); return source ? <a href={source} target="_blank" rel="noreferrer" className="workspace-image-value"><img src={source} alt="Pratinjau gambar"/></a> : <>—</>; });
registerFieldRenderer("binary", ({ field, value }) => field.widget === "image" ? display.image({ field, value, record: {} }) : value ? <a className="workspace-file-download" href={`data:application/octet-stream;base64,${value}`} download={field.label}><FileText/><span>{field.label}</span><Download/></a> : <>—</>);
registerFieldRenderer("pdf_viewer", display.binary);
registerFieldRenderer("attachment_image", display.image);
registerFieldRenderer("background_image", display.image);
registerFieldRenderer("many2many_binary", ({ value }) => <span className="workspace-tags">{Array.isArray(value) && value.length ? `${value.length} berkas` : "—"}</span>);
registerFieldRenderer("html", ({ value }) => <span className="line-clamp-2" dangerouslySetInnerHTML={{ __html: String(value || "") }}/>)
registerFieldRenderer("priority", ({ value }) => <span className="workspace-priority-read">{Number(value || 0) ? "★".repeat(Number(value)) : "☆"}</span>);
registerFieldRenderer("color", ({ value }) => <span className="workspace-color" style={{ backgroundColor: `hsl(${Number(value || 0) * 30} 65% 55%)` }}/>)
registerFieldRenderer("color_picker", display.color);
registerFieldRenderer("statinfo", ({ value }) => <strong className="tabular-nums">{text(value)}</strong>);
registerFieldRenderer("remaining_days", ({ value }) => <>{value ? new Date(String(value).replace(" ", "T") + (String(value).includes(" ") ? "Z" : "")).toLocaleDateString("id-ID", { dateStyle: "medium" }) : "—"}</>);
registerFieldRenderer("state_selection", display.badge);
registerFieldRenderer("label_selection", display.badge);
registerFieldRenderer("selection_badge", display.badge);
registerFieldRenderer("account_type_selection", display.selection);
registerFieldRenderer("float_without_trailing_zeros", ({ value }) => <>{Number(value || 0).toLocaleString("id-ID", { maximumFractionDigits: 12 })}</>);
registerFieldRenderer("activity_exception", ({ value }) => <>{value ? "Perlu perhatian" : "—"}</>);
registerFieldRenderer("json", ({ value }) => value && typeof value === "object" ? <pre className="workspace-json-value">{JSON.stringify(value, null, 2)}</pre> : <>—</>);
registerFieldRenderer("analytic_distribution", ({ value }) => value && typeof value === "object" ? <div className="workspace-distribution">{Object.entries(value as Record<string, unknown>).map(([account, percentage]) => <span key={account}><b>{account}</b><i>{Number(percentage).toLocaleString("id-ID")}%</i></span>)}</div> : <>—</>);
registerFieldRenderer("account-tax-totals-field", ({ value }) => value && typeof value === "object" ? <pre className="workspace-json-value">{JSON.stringify(value, null, 2)}</pre> : <>—</>);
registerFieldRenderer("monetary", ({ field, value, record }) => {
  const currency = field.currency_field && record[field.currency_field];
  const currencyCode = Array.isArray(currency) && /^[A-Z]{3}$/.test(String(currency[1])) ? String(currency[1]) : "IDR";
  try { return <>{new Intl.NumberFormat("id-ID", { style: "currency", currency: currencyCode, maximumFractionDigits: 0 }).format(Number(value || 0))}</>; }
  catch { return <>{text(value)}</>; }
});

const input = (type = "text"): Editor => ({ field, value, onChange }) => <Input type={type} placeholder={field.placeholder} value={value == null || value === false ? "" : String(value)} onChange={(event) => onChange(event.target.value)}/>;
editors.default = input();
editors.char = input();
editors.phone = input("tel");
editors.email = input("email");
editors.url = input("url");
editors.text = ({ field, value, onChange }) => <Textarea placeholder={field.placeholder} value={value == null || value === false ? "" : String(value)} onChange={(event) => onChange(event.target.value)}/>;
editors.html = editors.text;
editors.integer = ({ field, value, onChange }) => <Input type="number" placeholder={field.placeholder} value={value == null || value === false ? "" : String(value)} onChange={(event) => onChange(event.target.value === "" ? false : Number(event.target.value))}/>;
editors.float = editors.integer;
editors.monetary = editors.integer;
editors.percentage = editors.integer;
editors.float_time = ({ value, onChange }) => { const hours = Number(value || 0); const time = `${String(Math.floor(hours)).padStart(2, "0")}:${String(Math.round(hours % 1 * 60)).padStart(2, "0")}`; return <TimePicker value={time} onChange={(next) => { if (!next) return onChange(false); const [hour, minute] = next.split(":").map(Number); onChange(hour + minute / 60); }}/>; };
editors.boolean = ({ value, onChange }) => <Switch checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)}/>;
editors.boolean_toggle = editors.boolean;
editors.boolean_favorite = editors.boolean;
editors.selection = ({ field, value, onChange }) => <Select value={value === false || value == null ? "__empty__" : String(value)} onValueChange={(next) => onChange(next === "__empty__" ? false : next)}><SelectTrigger><SelectValue placeholder="Pilih..."/></SelectTrigger><SelectContent><SelectItem value="__empty__">Pilih...</SelectItem>{field.selection?.map(([key, label]) => <SelectItem key={key} value={key}>{label}</SelectItem>)}</SelectContent></Select>;
editors.radio = ({ field, value, onChange }) => <RadioGroup value={String(value ?? "")} onValueChange={onChange}>{field.selection?.map(([key, label]) => <label key={key} className="workspace-radio-option"><RadioGroupItem value={key}/><span>{label}</span></label>)}</RadioGroup>;
editors.date = ({ field, value, onChange }) => <DatePicker value={value ? String(value) : false} placeholder={field.placeholder || "Pilih tanggal"} onChange={onChange}/>;
editors.daterange = editors.date;
editors.datetime = ({ field, value, onChange }) => { const current = localDateTime(value); const [date, time = "00:00"] = current.split("T"); return <div className="workspace-datetime"><DatePicker value={date || false} placeholder={field.placeholder || "Pilih tanggal"} onChange={(next) => onChange(next ? `${next} ${time}:00` : false)}/><TimePicker value={time} onChange={(next) => onChange(date && next ? `${date} ${next}:00` : false)}/></div>; };
editors.binary = ({ field, value, onChange }) => <label className="workspace-file-input"><input type="file" accept={field.accept || (field.widget === "pdf_viewer" ? "application/pdf" : undefined)} onChange={(event) => { const file = event.target.files?.[0]; if (!file) return; const reader = new FileReader(); reader.onload = () => onChange(String(reader.result).split(",", 2)[1] || false); reader.readAsDataURL(file); }}/><Upload/><span>{value ? "Ganti berkas" : "Pilih berkas"}</span>{Boolean(value) && <Check/>}</label>;
editors.image = ({ value, onChange }) => <ImageUpload value={value} onChange={onChange}/>;
editors.one2many = (props) => <RelationTable {...props} editing/>;
editors.managed_addresses = (props) => <ManagedRelationCards {...props} editing/>;
editors.managed_contacts = editors.managed_addresses;
editors.managed_bank_accounts = editors.managed_addresses;
editors.managed_supplier_prices = editors.managed_addresses;
editors.many2many = (props) => props.field.relationView ? <RelationTable {...props} editing/> : <TagsEditor {...props}/>;
editors.many2many_tags = (props) => <TagsEditor {...props}/>;
editors.autosave_many2many_tags = editors.many2many_tags;
editors.many2many_tags_email = editors.many2many_tags;
editors.many2many_avatar_user = editors.many2many_tags;
editors.many2many_avatar_employee = editors.many2many_tags;
editors.many2many_checkboxes = (props) => <RelationCheckboxes {...props}/>;
editors.many2many_binary = editors.many2many_tags;
editors.priority = ({ field, value, onChange }) => <div className="workspace-priority">{(field.selection || [["0", "Normal"], ["1", "Penting"], ["2", "Sangat penting"]]).map(([key, label]) => <button type="button" key={key} className={String(value || "0") >= key && key !== "0" ? "active" : ""} title={label} onClick={() => onChange(key)}>★</button>)}</div>;
editors.color = ({ value, onChange }) => <div className="workspace-color-picker">{Array.from({ length: 12 }, (_, color) => <button type="button" key={color} aria-label={`Warna ${color + 1}`} className={Number(value || 0) === color ? "active" : undefined} style={{ backgroundColor: `hsl(${color * 30} 65% 55%)` }} onClick={() => onChange(color)}/>)}</div>;
editors.color_picker = editors.color;
editors.many2one = function RelationEditor({ actionId, field, value, onChange, parentValues }) {
  const controller = useRef<AbortController>();
  const [items, setItems] = useState<{ id: number; label: string }[]>([]);
  const [query, setQuery] = useState("");
  useEffect(() => {
    controller.current?.abort();
    controller.current = new AbortController();
    const params = relationParams(field, query, parentValues);
    const timeout = setTimeout(() => api<{ items: { id: number; label: string }[] }>(`/api/v1/ui/actions/${actionId}/relations/${field.name}?${params}`, { signal: controller.current?.signal }).then((response) => setItems(response.items)).catch((error) => { if (error.name !== "AbortError") setItems([]); }), 120);
    return () => { clearTimeout(timeout); controller.current?.abort(); };
  }, [actionId, field.name, field.parent, parentValues, query]);
  const selected = Array.isArray(value) ? { value: Number(value[0]), label: String(value[1]) } : undefined;
  return <Combobox options={items.map((item) => ({ value: item.id, label: item.label }))} value={selected} onSearch={setQuery} placeholder={field.placeholder || "Pilih..."} onChange={(next) => onChange(next ? [Number(next.value), next.label] : false)}/>;
};
editors.res_partner_many2one = editors.many2one;
editors.many2one_avatar_user = editors.many2one;
editors.many2one_avatar_employee = editors.many2one;
editors.many2one_barcode = editors.many2one;
editors.sol_product_many2one = editors.many2one;
editors.managed_customer_many2one = editors.many2one;
editors.managed_order_address_many2one = editors.many2one;
editors.managed_order_pricelist_many2one = editors.many2one;
editors.managed_order_payment_term_many2one = editors.many2one;
editors.managed_order_fiscal_position_many2one = editors.many2one;
editors.managed_order_warehouse_many2one = editors.many2one;
editors.managed_sale_product_many2one = editors.many2one;
editors.managed_sale_uom_many2one = editors.many2one;
editors.state_selection = editors.selection;
editors.label_selection = editors.selection;
editors.selection_badge = editors.selection;
editors.account_type_selection = editors.selection;
editors.attachment_image = editors.image;
editors.background_image = editors.image;
editors.pdf_viewer = editors.binary;
editors.CopyClipboardChar = editors.char;
editors.domain = editors.text;
editors.float_without_trailing_zeros = editors.float;
editors.json = JsonEditor;
editors.properties = JsonEditor;
editors.properties_definition = JsonEditor;
editors.analytic_distribution = JsonEditor;
editors["account-tax-totals-field"] = JsonEditor;

export function FieldValue(props: DisplayProps) { const Renderer = display[props.field.widget || props.field.type] || display[props.field.type] || display.default; return <Renderer {...props}/>; }
export function FieldEditor(props: EditorProps) { const Editor = editors[props.field.widget || props.field.type] || editors[props.field.type] || editors.default; return <Editor {...props}/>; }
