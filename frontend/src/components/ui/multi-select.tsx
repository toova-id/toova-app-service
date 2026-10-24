import { Check, ChevronDown, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "./button";
import { Checkbox } from "./checkbox";
import { Input } from "./input";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";
import { cn } from "@/lib/utils";

export interface MultiSelectOption { value: string | number; label: string }

export function MultiSelect({ options, value, onChange, onSearch, placeholder = "Pilih...", searchable = true, loading = false, className }: { options: MultiSelectOption[]; value: MultiSelectOption[]; onChange: (value: MultiSelectOption[]) => void; onSearch?: (query: string) => void; placeholder?: string; searchable?: boolean; loading?: boolean; className?: string }) {
  const [query, setQuery] = useState("");
  const selected = useMemo(() => new Set(value.map((item) => String(item.value))), [value]);
  const visible = options.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()));
  const toggle = (item: MultiSelectOption) => onChange(selected.has(String(item.value)) ? value.filter((entry) => String(entry.value) !== String(item.value)) : [...value, item]);
  return <Popover><div className={cn("luma-multi-select", className)}><PopoverTrigger asChild><button type="button" className="luma-multi-select-trigger" aria-label="Ubah pilihan"><span className="luma-multi-select-values">{value.length ? value.map((item) => <span key={String(item.value)}><span>{item.label}</span><span role="button" tabIndex={0} aria-label={`Hapus ${item.label}`} onClick={(event) => { event.stopPropagation(); toggle(item); }} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); event.stopPropagation(); toggle(item); } }}><X/></span></span>) : <span className="luma-multi-select-placeholder">{placeholder}</span>}</span><ChevronDown/></button></PopoverTrigger></div><PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] min-w-56 p-1">{searchable && <Input className="mb-1" value={query} onChange={(event) => { setQuery(event.target.value); onSearch?.(event.target.value); }} placeholder="Cari..."/>}<div className="luma-multi-select-options">{visible.map((item) => <button type="button" key={String(item.value)} onClick={() => toggle(item)}><Checkbox tabIndex={-1} checked={selected.has(String(item.value))} aria-hidden="true"/><span>{item.label}</span>{selected.has(String(item.value)) && <Check/>}</button>)}{loading && <span className="luma-multi-select-empty">Memuat...</span>}{!loading && !visible.length && <span className="luma-multi-select-empty">Tidak ada pilihan</span>}</div>{value.length > 0 && <div className="border-t p-1"><Button type="button" variant="ghost" size="sm" className="w-full" onClick={() => onChange([])}>Hapus semua</Button></div>}</PopoverContent></Popover>;
}
