import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowLeft, ArrowRight, Boxes, CheckCircle2, Clock3, LogOut, MapPin, PackageCheck, RefreshCw, ScanLine, Truck } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import type { ClientActionProps } from "@toova/features/feature-registry";
import { useSession } from "@toova/app/session";
import { api } from "@toova/lib/api";
import { Button } from "@toova/components/ui/button";
import { cn } from "@toova/lib/utils";

type Operation = {
  id: number; name: string; kind: string; status: string; progress: string; partner: string; origin: string;
  scheduledDate?: string; source: string; destination: string; state: string; late: boolean;
};
type Response = { items: Operation[]; counts: { ready: number; waiting: number; late: number; total: number } };
type Filter = "all" | "ready" | "waiting" | "late";

const icon = (kind: string) => kind === "Penerimaan" ? <PackageCheck/> : kind === "Pengiriman" ? <Truck/> : <Boxes/>;
const date = (value?: string) => value ? new Date(value.replace(" ", "T") + "Z").toLocaleString("id-ID", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "Belum dijadwalkan";
const detailPath = (item: Operation) => item.kind === "Pengiriman" ? `/app/persediaan/pengiriman/${item.id}` : undefined;

export default function WarehousePage(_props: ClientActionProps) {
  const session = useSession();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState<Response>();
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const load = () => { setLoading(true); setError(undefined); api<Response>("/api/v1/warehouse/operations").then(setData).catch((reason) => setError(reason.message)).finally(() => setLoading(false)); };
  useEffect(load, []);
  const selected = data?.items.find((item) => item.id === Number(searchParams.get("task")));
  const items = useMemo(() => (data?.items || []).filter((item) => {
    if (filter === "ready" && item.state !== "assigned") return false;
    if (filter === "waiting" && !["waiting", "confirmed", "partially_available"].includes(item.state)) return false;
    if (filter === "late" && !item.late) return false;
    const needle = query.trim().toLocaleLowerCase("id-ID");
    return !needle || [item.name, item.kind, item.partner, item.origin].some((value) => value.toLocaleLowerCase("id-ID").includes(needle));
  }), [data, filter, query]);

  return <div className="toova-warehouse-mode">
    <header className="toova-warehouse-bar"><div><span className="toova-brand-mark"/><strong>Mode Gudang</strong><i>{session.company.name}</i></div><div><span className="online">Online</span><b>{session.user.name}</b><Button asChild variant="ghost" size="sm"><Link to="/app"><LogOut/>ERP</Link></Button></div></header>
    {selected ? <main className="toova-warehouse-execution">
      <header><button onClick={() => setSearchParams({})}><ArrowLeft/>Antrean</button><div><span>{selected.kind}</span><h1>{selected.name}</h1><p>{selected.partner || selected.origin || "Operasi internal"}</p></div><b>{selected.status}</b></header>
      <section className="toova-warehouse-route"><MapPin/><div><span>Rute barang</span><strong>{selected.source} <ArrowRight/> {selected.destination}</strong></div></section>
      <section className="toova-warehouse-focus"><ScanLine/><span>Siap scan</span><h2>Scan produk atau lokasi</h2><p>Mode eksekusi fokus memakai task native yang sama. Rincian quantity dan lot tersedia untuk Pengiriman; operasi lain masuk bertahap setelah contract masing-masing siap.</p><input autoFocus placeholder="Scan barcode..."/>{detailPath(selected) ? <Button asChild><Link to={detailPath(selected)!}>Buka rincian barang<ArrowRight/></Link></Button> : <Button disabled>Rincian segera tersedia</Button>}</section>
      <footer><span>{selected.progress}</span><time>{date(selected.scheduledDate)}</time></footer>
    </main> : <main className="toova-warehouse-workspace">
      <section className="toova-warehouse-heading"><div><span>Antrean operasional</span><h1>Pekerjaan gudang</h1><p>Pilih task, proses barang, lalu selesaikan dengan workflow stock native.</p></div><Button variant="outline" onClick={load} disabled={loading}><RefreshCw className={cn(loading && "animate-spin")}/>Muat ulang</Button></section>
      <section className="toova-warehouse-metrics">
        <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}><Boxes/><span><small>Semua task</small><strong>{data?.counts.total || 0}</strong></span></button>
        <button className={filter === "ready" ? "active" : ""} onClick={() => setFilter("ready")}><CheckCircle2/><span><small>Siap diproses</small><strong>{data?.counts.ready || 0}</strong></span></button>
        <button className={filter === "waiting" ? "active" : ""} onClick={() => setFilter("waiting")}><Clock3/><span><small>Menunggu</small><strong>{data?.counts.waiting || 0}</strong></span></button>
        <button className={filter === "late" ? "active" : ""} onClick={() => setFilter("late")}><AlertTriangle/><span><small>Terlambat</small><strong>{data?.counts.late || 0}</strong></span></button>
      </section>
      <section className="toova-warehouse-tools"><label><ScanLine/><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Scan atau cari nomor, sumber, pelanggan..."/></label><span>{items.length} task ditampilkan</span></section>
      {error && <div className="toova-warehouse-error"><AlertTriangle/><span>{error}</span><button onClick={load}>Coba lagi</button></div>}
      <section className="toova-warehouse-queue">
        {items.map((item) => <button key={item.id} onClick={() => setSearchParams({ task: String(item.id) })} className="toova-warehouse-task">
          <div className="toova-warehouse-task-icon">{icon(item.kind)}</div><div className="toova-warehouse-task-main"><header><span>{item.kind}</span>{item.late && <i>Terlambat</i>}<b>{item.name}</b></header><h2>{item.partner || item.origin || "Operasi internal"}</h2><p><MapPin/>{item.source} <ArrowRight/> {item.destination}</p></div><div className="toova-warehouse-task-progress"><strong>{item.status}</strong><span>{item.progress}</span><time>{date(item.scheduledDate)}</time></div><ArrowRight className="toova-warehouse-task-open"/>
        </button>)}
        {!loading && !items.length && <div className="toova-warehouse-empty"><PackageCheck/><strong>Tidak ada task pada antrean ini</strong><span>Ubah filter atau scan nomor operasi lain.</span></div>}
      </section>
    </main>}
  </div>;
}
