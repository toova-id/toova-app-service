import { addMonths, format, parseISO } from "date-fns";
import { id } from "date-fns/locale";
import { CalendarRange, X } from "lucide-react";
import { useState } from "react";
import type { DateRange } from "react-day-picker";
import { Button } from "./button";
import { Calendar } from "./calendar";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";
import { cn } from "@/lib/utils";

export function DateRangePicker({ from, to, onChange, disabled }: { from?: string | false; to?: string | false; onChange: (range: { from: string | false; to: string | false }) => void; disabled?: boolean }) {
  const range = { from: from ? parseISO(String(from).slice(0, 10)) : undefined, to: to ? parseISO(String(to).slice(0, 10)) : undefined };
  const [month, setMonth] = useState(range.from || new Date());
  const label = range.from ? range.to ? `${format(range.from, "dd MMM yyyy", { locale: id })} – ${format(range.to, "dd MMM yyyy", { locale: id })}` : format(range.from, "dd MMM yyyy", { locale: id }) : "Pilih rentang tanggal";
  const change = (next: DateRange | undefined) => onChange({ from: next?.from ? format(next.from, "yyyy-MM-dd") : false, to: next?.to ? format(next.to, "yyyy-MM-dd") : false });
  return <Popover><div className="relative"><PopoverTrigger asChild><Button type="button" variant="outline" disabled={disabled} className={cn("h-8 w-full justify-start px-2.5 pr-8 text-left font-normal shadow-[var(--shadow-control)]", !range.from && "text-muted-foreground")}><CalendarRange className="mr-2 h-3.5 w-3.5"/>{label}</Button></PopoverTrigger>{range.from && !disabled && <button type="button" className="luma-date-clear" aria-label="Hapus rentang tanggal" onClick={() => onChange({ from: false, to: false })}><X/></button>}</div><PopoverContent className="w-auto p-0" align="start"><Calendar mode="range" locale={id} month={month} onMonthChange={setMonth} selected={range} onSelect={change} numberOfMonths={2} defaultMonth={range.from || addMonths(new Date(), -1)} initialFocus/></PopoverContent></Popover>;
}
