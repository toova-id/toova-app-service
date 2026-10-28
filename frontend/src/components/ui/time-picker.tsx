import { Clock3 } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./select";

const hours = Array.from({ length: 24 }, (_, value) => String(value).padStart(2, "0"));
const minutes = Array.from({ length: 60 }, (_, value) => String(value).padStart(2, "0"));

export function TimePicker({ value, onChange, disabled }: { value?: string | false; onChange: (value: string | false) => void; disabled?: boolean }) {
  const [hour = "00", minute = "00"] = value ? String(value).slice(0, 5).split(":") : [];
  return <div className="toova-time-picker"><Clock3/><Select value={hour || "00"} onValueChange={(next) => onChange(`${next}:${minute || "00"}`)} disabled={disabled}><SelectTrigger aria-label="Jam"><SelectValue/></SelectTrigger><SelectContent>{hours.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select><span>:</span><Select value={minute || "00"} onValueChange={(next) => onChange(`${hour || "00"}:${next}`)} disabled={disabled}><SelectTrigger aria-label="Menit"><SelectValue/></SelectTrigger><SelectContent>{minutes.map((item) => <SelectItem key={item} value={item}>{item}</SelectItem>)}</SelectContent></Select></div>;
}
