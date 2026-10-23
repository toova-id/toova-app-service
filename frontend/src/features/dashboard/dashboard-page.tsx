import { Activity, ArrowRight, Boxes, CircleDollarSign, ClipboardCheck, RefreshCw, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { firstAction, useNavigation } from "@/app/navigation";
import { getNavigationIcon } from "../feature-registry";
import { useSession } from "@/app/session";

const metrics = [
  { label: "Penjualan bulan ini", value: "Rp 0", detail: "Belum ada transaksi", icon: CircleDollarSign },
  { label: "Pesanan aktif", value: "0", detail: "Pesanan berjalan", icon: ClipboardCheck },
  { label: "Item persediaan", value: "0", detail: "Produk terdaftar", icon: Boxes },
  { label: "Anggota tim", value: "1", detail: "Pengguna aktif", icon: Users },
];

export default function DashboardPage() {
  const { user, company } = useSession();
  const apps = useNavigation().map((item) => ({ item, action: firstAction(item) })).filter(({ action }) => action);
  return <div className="workspace-home">
    <header className="workspace-home-header"><div><h1>Selamat datang, {user.name.split(" ")[0]}</h1><p>{company.name}</p></div><div className="workspace-home-actions"><span>Diperbarui sekarang</span><Button variant="outline"><RefreshCw className="h-3.5 w-3.5"/>Segarkan</Button></div></header>
    <section className="workspace-home-section" aria-labelledby="workspace-apps-title"><div className="workspace-section-header"><h2 id="workspace-apps-title">Aplikasi</h2><span>{apps.length} aplikasi</span></div><div className="workspace-app-grid">{apps.map(({ item, action }) => { const Icon = getNavigationIcon(item.module, item.xmlid); return <Link key={item.id} to={action!.path!} className="workspace-app-tile"><span className="workspace-app-icon">{Icon ? <Icon/> : item.label.slice(0, 1)}</span><span className="workspace-app-copy"><strong>{item.label}</strong><small>Buka aplikasi</small></span><ArrowRight className="workspace-app-arrow"/></Link>; })}</div></section>
    <section className="workspace-home-section" aria-labelledby="workspace-pulse-title"><div className="workspace-section-header"><h2 id="workspace-pulse-title">Ringkasan bisnis</h2><span>Data ruang kerja saat ini</span></div><div className="workspace-metric-grid">{metrics.map(({ label, value, detail, icon: Icon }) => <article key={label}><div className="workspace-metric-header"><span>{label}</span><Icon/></div><strong>{value}</strong><small>{detail}</small></article>)}</div><div className="workspace-panel-grid"><article className="workspace-panel workspace-panel-wide"><header><div><strong>Aktivitas bisnis</strong><span>Penjualan, pembelian, dan persediaan</span></div><span>Hari ini</span></header><div className="workspace-empty"><Activity/><strong>Belum ada aktivitas</strong><span>Transaksi pertama akan tampil di sini.</span></div></article><article className="workspace-panel"><header><div><strong>Perlu perhatian</strong><span>Tugas dan pengecualian prioritas</span></div></header><div className="workspace-status-ok"><i/><div><strong>Semua sistem normal</strong><span>Tidak ada tindakan mendesak.</span></div></div></article></div></section>
  </div>;
}
