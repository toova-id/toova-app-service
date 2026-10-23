import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
export default function NotFoundPage() { return <div className="grid min-h-[60vh] place-items-center text-center"><div><p className="text-sm font-medium text-primary">404</p><h1 className="mt-2 text-3xl font-bold">Halaman belum tersedia</h1><p className="mt-2 text-muted-foreground">Fitur ini akan hadir lewat modul produk terkait.</p><Button asChild className="mt-6"><Link to="/app">Kembali ke beranda</Link></Button></div></div>; }
