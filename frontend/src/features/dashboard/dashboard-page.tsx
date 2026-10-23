import { ArrowUpRight, Boxes, CircleDollarSign, ClipboardCheck, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useSession } from "@/app/session";

const metrics = [
  { label: "Penjualan bulan ini", value: "Rp 0", detail: "Siap menerima transaksi", icon: CircleDollarSign },
  { label: "Pesanan aktif", value: "0", detail: "Belum ada pesanan", icon: ClipboardCheck },
  { label: "Item persediaan", value: "0", detail: "Sinkron dengan gudang", icon: Boxes },
  { label: "Anggota tim", value: "1", detail: "Termasuk Anda", icon: Users },
];
export default function DashboardPage() {
  const { user, company } = useSession();
  return <div className="space-y-8"><section className="flex flex-col justify-between gap-4 md:flex-row md:items-end"><div><Badge className="mb-3 w-fit bg-cyan-100 text-cyan-800">Workspace aktif</Badge><h1 className="text-3xl font-bold tracking-tight">Selamat datang, {user.name.split(" ")[0]}</h1><p className="mt-2 text-muted-foreground">Ringkasan operasional {company.name} hari ini.</p></div><p className="text-sm text-muted-foreground">Data diperbarui langsung dari ERP</p></section>
    <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map(({ label, value, detail, icon: Icon }) => <Card key={label}><CardHeader className="flex-row items-center justify-between pb-2"><CardDescription>{label}</CardDescription><Icon className="h-4 w-4 text-muted-foreground"/></CardHeader><CardContent><p className="text-2xl font-bold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{detail}</p></CardContent></Card>)}</section>
    <section className="grid gap-4 xl:grid-cols-[1.4fr_1fr]"><Card><CardHeader><CardTitle>Aktivitas bisnis</CardTitle><CardDescription>Arus kerja lintas penjualan, pembelian, dan gudang.</CardDescription></CardHeader><CardContent><div className="grid min-h-64 place-items-center rounded-lg border border-dashed bg-muted/30 text-center"><div><ArrowUpRight className="mx-auto h-8 w-8 text-muted-foreground"/><p className="mt-3 font-medium">Belum ada aktivitas</p><p className="mt-1 text-sm text-muted-foreground">Transaksi pertama akan tampil di sini.</p></div></div></CardContent></Card><Card><CardHeader><CardTitle>Perlu perhatian</CardTitle><CardDescription>Tugas dan pengecualian prioritas.</CardDescription></CardHeader><CardContent><p className="rounded-lg bg-emerald-50 p-4 text-sm text-emerald-800">Semua sistem normal. Tidak ada tindakan mendesak.</p></CardContent></Card></section>
  </div>;
}
