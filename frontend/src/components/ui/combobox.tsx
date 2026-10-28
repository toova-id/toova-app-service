import { Check, ChevronsUpDown, X } from "lucide-react";
import { useState } from "react";
import { Input } from "./input";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";
import { cn } from "@/lib/utils";

export interface ComboboxOption { value: string | number; label: string }

export function Combobox({ options, value, onChange, onSearch, placeholder = "Pilih...", searchPlaceholder = "Cari...", loading = false, clearable = true }: { options: ComboboxOption[]; value?: ComboboxOption; onChange: (value?: ComboboxOption) => void; onSearch?: (query: string) => void; placeholder?: string; searchPlaceholder?: string; loading?: boolean; clearable?: boolean }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const select = (option?: ComboboxOption) => { onChange(option); setOpen(false); setQuery(""); onSearch?.(""); };
  return <Popover open={open} onOpenChange={setOpen}><div className="relative"><PopoverTrigger asChild><button type="button" role="combobox" aria-expanded={open} className={cn("toova-combobox-trigger", !value && "text-muted-foreground", value && clearable && "pr-8")}><span>{value?.label || placeholder}</span>{!value && <ChevronsUpDown/>}</button></PopoverTrigger>{value && clearable && <button type="button" className="toova-combobox-clear" aria-label="Hapus pilihan" onClick={() => select()}><X/></button>}</div><PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] min-w-56 p-1"><Input autoFocus value={query} onChange={(event) => { setQuery(event.target.value); onSearch?.(event.target.value); }} placeholder={searchPlaceholder}/><div className="toova-combobox-options">{options.map((option) => <button type="button" key={String(option.value)} onClick={() => select(option)}><span>{option.label}</span>{String(option.value) === String(value?.value) && <Check/>}</button>)}{loading && <span>Memuat...</span>}{!loading && !options.length && <span>Tidak ada pilihan</span>}</div></PopoverContent></Popover>;
}
