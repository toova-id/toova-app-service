import { Suspense, useEffect, useState } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { api, setCsrfToken } from "@/lib/api";
import { AppShell } from "./app-shell";
import { applyManagedNavigation } from "./managed-navigation";
import { routes } from "./features";
import { NavigationProvider } from "./navigation";
import { SessionProvider } from "./session";
import type { ServerNavigationItem, Session } from "./types";
import { AppLoading, LoadError, ViewLoading } from "@/components/loading";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [navigation, setNavigation] = useState<ServerNavigationItem[]>([]);
  const [error, setError] = useState<string>();
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError(undefined);
    Promise.all([
      api<Session>("/api/v1/session", { signal: controller.signal }),
      api<{ items: ServerNavigationItem[] }>("/api/v1/ui/navigation", { signal: controller.signal }),
    ]).then(([currentSession, currentNavigation]) => { setCsrfToken(currentSession.csrfToken); setSession(currentSession); setNavigation(applyManagedNavigation(currentNavigation.items)); }).catch((reason) => { if (reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [attempt]);
  if (error) return <LoadError message={error} retry={() => setAttempt((value) => value + 1)}/>;
  if (!session) return <AppLoading/>;
  return <SessionProvider session={session}><NavigationProvider items={navigation}><BrowserRouter><Routes><Route element={<AppShell/>}>{routes.filter((route) => !route.module || session.modules.includes(route.module)).map(({ path, component: Component }) => <Route key={path} path={path} element={<Suspense fallback={<ViewLoading/>}><Component/></Suspense>}/>)}</Route></Routes></BrowserRouter></NavigationProvider></SessionProvider>;
}
