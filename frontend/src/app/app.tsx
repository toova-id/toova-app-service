import { Suspense, useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { api } from "@/lib/api";
import { AppShell } from "./app-shell";
import { routes } from "./features";
import { SessionProvider } from "./session";
import type { Session } from "./types";
import { Skeleton } from "@/components/ui/skeleton";

function Loading() { return <div className="space-y-4"><Skeleton className="h-9 w-64"/><Skeleton className="h-40 w-full"/><Skeleton className="h-64 w-full"/></div>; }

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [error, setError] = useState<string>();
  useEffect(() => { api<Session>("/api/v1/session").then(setSession).catch((reason) => setError(reason.message)); }, []);
  if (error) return <div className="grid min-h-screen place-items-center p-6"><div className="max-w-md rounded-xl border bg-card p-8 text-center shadow-panel"><h1 className="text-xl font-semibold">Ruang kerja gagal dimuat</h1><p className="mt-2 text-sm text-muted-foreground">{error}</p></div></div>;
  if (!session) return <div className="mx-auto max-w-7xl p-8"><Loading/></div>;

  return <SessionProvider session={session}><BrowserRouter><Routes><Route element={<AppShell/>}>{routes.filter((route) => !route.module || session.modules.includes(route.module)).map(({ path, component: Component }) => <Route key={path} path={path} element={<Suspense fallback={<Loading/>}><Component/></Suspense>}/>)}</Route></Routes></BrowserRouter></SessionProvider>;
}
