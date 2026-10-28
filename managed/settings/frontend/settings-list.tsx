import { Plus, Search, ShieldCheck, UserRound } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "@toova/components/ui/button";
import { Input } from "@toova/components/ui/input";
import type { CustomListViewProps } from "@toova/views/view-registry";

function SettingsCards({ props, kind }: { props: CustomListViewProps; kind: "users" | "roles" }) {
  const { schema, basePath, data, query, loading, onQuery } = props;
  const navigate = useNavigate();
  const Icon = kind === "users" ? UserRound : ShieldCheck;
  return <div className="toova-settings-collection"><header><label className="toova-settings-collection-search"><Search/><Input value={query} onChange={(event) => onQuery(event.target.value)} placeholder="Cari..."/></label>{schema.list.create && <Button onClick={() => navigate(`${basePath}/new`)}><Plus/>Tambah</Button>}</header><div className="toova-settings-collection-list">{data?.items.map((item) => <button key={String(item.id)} type="button" onClick={() => navigate(`${basePath}/${item.id}`)}><span><Icon/></span><strong>{String(item.name || "Tanpa nama")}</strong><small>{kind === "users" ? String(item.login || "—") : `${Array.isArray(item.user_ids) ? item.user_ids.length : 0} pengguna`}</small><b className={item.active === false ? "inactive" : "active"}>{item.active === false ? "Nonaktif" : "Aktif"}</b></button>)}{loading && !data && <div className="workspace-loading">Memuat...</div>}{data && !data.items.length && <div className="workspace-list-empty"><Icon/><strong>Belum ada data</strong></div>}</div></div>;
}

export function UsersSettingsList(props: CustomListViewProps) { return <SettingsCards props={props} kind="users"/>; }
export function RolesSettingsList(props: CustomListViewProps) { return <SettingsCards props={props} kind="roles"/>; }
