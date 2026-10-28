import { LoaderCircle, RotateCcw } from "lucide-react";
import { Button } from "./ui/button";
import { Skeleton } from "./ui/skeleton";

export function AppLoading() {
  return <div className="toova-boot" role="status"><span className="toova-brand-mark"/><strong>Toova</strong><span>Menyiapkan ruang kerja...</span></div>;
}

export function ViewLoading() {
  return <div className="workspace-view-loading" role="status" aria-label="Memuat data"><div className="workspace-loading-header"><Skeleton className="h-5 w-44"/><Skeleton className="h-8 w-72"/><Skeleton className="h-8 w-16"/></div><div className="space-y-px">{Array.from({ length: 8 }, (_, index) => <Skeleton key={index} className="h-11 w-full rounded-none opacity-[.55]"/>)}</div></div>;
}

export function InlineLoading() { return <span className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground"><LoaderCircle className="h-3.5 w-3.5 animate-spin"/>Memuat...</span>; }

export function LoadError({ message, retry }: { message: string; retry?: () => void }) {
  return <div className="workspace-error" role="alert"><strong>Data gagal dimuat</strong><span>{message}</span>{retry && <Button variant="outline" size="sm" onClick={retry}><RotateCcw className="h-3 w-3"/>Coba lagi</Button>}</div>;
}
