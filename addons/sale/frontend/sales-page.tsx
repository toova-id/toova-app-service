import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Plus, Search } from "lucide-react";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface SaleOrder { id: number; name: string; customer: string; date: string | null; state: string; stateLabel: string; total: number; currency: string }
interface SalesResponse { items: SaleOrder[]; page: number; pageSize: number; total: number }
const money = (value: number, currency: string) => new Intl.NumberFormat("id-ID", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
export default function SalesPage() {
  const [data, setData] = useState<SalesResponse>();
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string>();
  useEffect(() => { const timeout = setTimeout(() => api<SalesResponse>(`/api/v1/sales/orders?page=${page}&q=${encodeURIComponent(query)}`).then(setData).catch((reason) => setError(reason.message)), 200); return () => clearTimeout(timeout); }, [page, query]);
  return <div className="space-y-6"><header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-medium text-primary">Penjualan</p><h1 className="mt-1 text-3xl font-bold tracking-tight">Pesanan penjualan</h1><p className="mt-2 text-muted-foreground">Kelola penawaran dan pesanan pelanggan.</p></div><Button disabled title="Pembuatan pesanan masuk vertical slice berikutnya"><Plus className="h-4 w-4"/>Pesanan baru</Button></header>
    <Card className="overflow-hidden"><div className="flex items-center border-b p-4"><div className="flex w-full max-w-sm items-center gap-2 rounded-md border px-3"><Search className="h-4 w-4 text-muted-foreground"/><input value={query} onChange={(event) => { setPage(1); setQuery(event.target.value); }} className="h-10 w-full bg-transparent text-sm outline-none" placeholder="Cari nomor atau pelanggan..."/></div></div>
      {error ? <p className="p-6 text-sm text-destructive">{error}</p> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-muted/40 text-left text-xs uppercase tracking-wide text-muted-foreground"><tr><th className="px-5 py-3">Nomor</th><th className="px-5 py-3">Pelanggan</th><th className="px-5 py-3">Tanggal</th><th className="px-5 py-3">Status</th><th className="px-5 py-3 text-right">Total</th></tr></thead><tbody>{data?.items.map((order) => <tr key={order.id} className="border-t hover:bg-muted/30"><td className="px-5 py-4 font-medium">{order.name}</td><td className="px-5 py-4">{order.customer}</td><td className="px-5 py-4 text-muted-foreground">{order.date ? new Date(order.date).toLocaleDateString("id-ID") : "—"}</td><td className="px-5 py-4"><Badge>{order.stateLabel}</Badge></td><td className="px-5 py-4 text-right font-medium">{money(order.total, order.currency)}</td></tr>)}</tbody></table>{data && data.items.length === 0 && <p className="p-10 text-center text-muted-foreground">Belum ada pesanan penjualan.</p>}</div>}
      <footer className="flex items-center justify-between border-t px-5 py-3 text-sm text-muted-foreground"><span>{data?.total ?? 0} pesanan</span><div className="flex gap-1"><Button variant="outline" size="icon" disabled={page <= 1} onClick={() => setPage((value) => value - 1)} aria-label="Halaman sebelumnya"><ChevronLeft className="h-4 w-4"/></Button><Button variant="outline" size="icon" disabled={!data || page * data.pageSize >= data.total} onClick={() => setPage((value) => value + 1)} aria-label="Halaman berikutnya"><ChevronRight className="h-4 w-4"/></Button></div></footer></Card>
  </div>;
}
