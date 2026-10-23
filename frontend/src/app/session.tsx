import { createContext, useContext, type ReactNode } from "react";
import type { Session } from "./types";

const SessionContext = createContext<Session | null>(null);
export function SessionProvider({ session, children }: { session: Session; children: ReactNode }) { return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>; }
export function useSession() {
  const session = useContext(SessionContext);
  if (!session) throw new Error("SessionProvider missing");
  return session;
}
