import { ChevronDown, ChevronLeft, ChevronRight, Download, Filter, MoreHorizontal, Plus, RefreshCw, Search, Trash2 } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FieldValue } from "./field-registry";
import type { ActionSchema, RecordsResponse } from "./types";

interface Props {
  schema: ActionSchema; basePath: string; data?: RecordsResponse; query: string; page: number; loading: boolean;
  selected: number[]; filters: string[]; onQuery: (value: string) => void; onPage: (value: number) => void;
  onSelected: (value: number[]) => void; onFilters: (value: string[]) => void; onRefresh: () => void;
  onDelete: () => void; onBulkAction: (id: number) => void;
}

export function ListView({ schema, basePath, data, query, page, loading, selected, filters, onQuery, onPage, onSelected, onFilters, onRefresh, onDelete, onBulkAction }: Props) {
  const navigate = useNavigate();
  const visibleIds = data?.items.map((record) => Number(record.id)) ?? [];
  const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selected.includes(id));
  const exportUrl = `/api/v1/ui/actions/${schema.id}/export.csv?${new URLSearchParams({ ...(selected.length ? { ids: selected.join(",") } : {}), ...(query ? { q: query } : {}), ...(filters.length ? { filters: filters.join(",") } : {}) })}`;
  const toggleAll = () => onSelected(allSelected ? selected.filter((id) => !visibleIds.includes(id)) : [...new Set([...selected, ...visibleIds])]);
  const toggleOne = (id: number) => onSelected(selected.includes(id) ? selected.filter((item) => item !== id) : [...selected, id]);

  return <div className="workspace-view">
    <header className="workspace-control-panel">
      <div className="workspace-control-title"><h1>{schema.list.title}</h1>{selected.length > 0 && <span>{selected.length} dipilih</span>}</div>
      <label className="workspace-search"><Search/><input value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Cari data..."/>{loading && <RefreshCw className="animate-spin"/>}</label>
      <div className="workspace-control-actions">
        {schema.list.filters.length > 0 && <DropdownMenu.Root><DropdownMenu.Trigger asChild><Button variant="outline"><Filter className="h-3.5 w-3.5"/>Filter{filters.length > 0 && <b>{filters.length}</b>}<ChevronDown className="h-3 w-3"/></Button></DropdownMenu.Trigger><DropdownMenu.Portal><DropdownMenu.Content align="end" className="z-50 min-w-52 rounded-md border bg-card p-1 shadow-[var(--shadow-floating)]">{schema.list.filters.map((item) => <DropdownMenu.CheckboxItem key={item.name} checked={filters.includes(item.name)} onCheckedChange={(checked) => onFilters(checked ? [...filters, item.name] : filters.filter((name) => name !== item.name))} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-[11px] outline-none hover:bg-muted"><span className="w-3">{filters.includes(item.name) ? "✓" : ""}</span>{item.label}</DropdownMenu.CheckboxItem>)}</DropdownMenu.Content></DropdownMenu.Portal></DropdownMenu.Root>}
        {selected.length > 0 && <DropdownMenu.Root><DropdownMenu.Trigger asChild><Button variant="outline"><MoreHorizontal className="h-3.5 w-3.5"/>Aksi<ChevronDown className="h-3 w-3"/></Button></DropdownMenu.Trigger><DropdownMenu.Portal><DropdownMenu.Content align="end" className="z-50 min-w-48 rounded-md border bg-card p-1 shadow-[var(--shadow-floating)]">{schema.list.actions.filter((item) => item.kind === "action").map((item) => <DropdownMenu.Item key={item.id} onSelect={() => onBulkAction(item.id)} className="cursor-pointer rounded px-2 py-1.5 text-[11px] outline-none hover:bg-muted">{item.label}</DropdownMenu.Item>)}{schema.list.export && <DropdownMenu.Item asChild><a href={exportUrl} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-[11px] outline-none hover:bg-muted"><Download className="h-3.5 w-3.5"/>Export CSV</a></DropdownMenu.Item>}{schema.list.delete && <DropdownMenu.Item onSelect={onDelete} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-[11px] text-destructive outline-none hover:bg-muted"><Trash2 className="h-3.5 w-3.5"/>Hapus</DropdownMenu.Item>}</DropdownMenu.Content></DropdownMenu.Portal></DropdownMenu.Root>}
        {selected.length === 0 && schema.list.export && <Button asChild variant="outline"><a href={exportUrl}><Download className="h-3.5 w-3.5"/>Export</a></Button>}
        {schema.list.create && <Button asChild><Link to={`${basePath}/new`}><Plus className="h-3.5 w-3.5"/>Baru</Link></Button>}
      </div>
    </header>

    <div className="workspace-list"><div className="overflow-x-auto"><table><thead><tr><th className="workspace-select-cell"><input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="Pilih semua pada halaman"/></th>{schema.list.columns.map((field) => <th key={field.name}>{field.label}</th>)}</tr></thead><tbody>{loading && !data ? Array.from({ length: 8 }, (_, index) => <tr key={index}><td colSpan={schema.list.columns.length + 1}><Skeleton className="h-5 w-full rounded-sm"/></td></tr>) : data?.items.map((record) => { const id = Number(record.id); return <tr key={id} className={selected.includes(id) ? "workspace-row-selected" : undefined} onClick={(event) => { if (!(event.target as HTMLElement).closest("a,button,input,label")) navigate(`${basePath}/${id}`); }}><td className="workspace-select-cell"><input type="checkbox" checked={selected.includes(id)} onChange={() => toggleOne(id)} aria-label={`Pilih ${id}`}/></td>{schema.list.columns.map((field, index) => <td key={field.name}>{index === 0 ? <Link className="font-medium hover:text-accent-foreground" to={`${basePath}/${id}`}><FieldValue field={field} value={record[field.name]} record={record}/></Link> : <FieldValue field={field} value={record[field.name]} record={record}/>}</td>)}</tr>; })}</tbody></table>{data && !data.items.length && !loading && <div className="workspace-list-empty"><Search/><strong>Belum ada data</strong><span>Ubah filter atau buat data baru.</span></div>}</div><footer className="workspace-list-footer"><span>{data?.total ?? 0} data</span><div><Button variant="ghost" size="icon" onClick={onRefresh} disabled={loading} aria-label="Segarkan"><RefreshCw className={loading ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"}/></Button><span className="workspace-footer-divider"/><Button variant="outline" size="icon" disabled={loading || page <= 1} onClick={() => onPage(page - 1)}><ChevronLeft className="h-3.5 w-3.5"/></Button><Button variant="outline" size="icon" disabled={loading || !data || page * data.pageSize >= data.total} onClick={() => onPage(page + 1)}><ChevronRight className="h-3.5 w-3.5"/></Button></div></footer></div>
  </div>;
}
