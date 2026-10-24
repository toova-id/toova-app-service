import { format, parseISO } from "date-fns";
import { id } from "date-fns/locale";
import { CalendarIcon, X } from "lucide-react";
import { useState } from "react";
import { Button } from "./button";
import { Calendar } from "./calendar";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";
import { cn } from "@/lib/utils";

export function DatePicker({ value, onChange, placeholder = "Pilih tanggal", disabled }: { value?: string | false; onChange: (value: string | false) => void; placeholder?: string; disabled?: boolean }) {
  const selected = value ? parseISO(String(value).slice(0, 10)) : undefined;
  const [month, setMonth] = useState<Date>(selected || new Date());
  return <Popover><div className="relative"><PopoverTrigger asChild><Button type="button" variant="outline" disabled={disabled} className={cn("h-8 w-full justify-start px-2.5 pr-8 text-left font-normal shadow-[var(--shadow-control)]", !selected && "text-muted-foreground")}><CalendarIcon className="mr-2 h-3.5 w-3.5"/>{selected ? format(selected, "PPP", { locale: id }) : placeholder}</Button></PopoverTrigger>{selected && !disabled && <button type="button" className="luma-date-clear" aria-label="Hapus tanggal" onClick={() => onChange(false)}><X/></button>}</div><PopoverContent className="w-auto p-0" align="start"><Calendar mode="single" locale={id} month={month} onMonthChange={setMonth} selected={selected} onSelect={(date) => onChange(date ? format(date, "yyyy-MM-dd") : false)} initialFocus/></PopoverContent></Popover>;
}
