import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, apiMutation } from "@/lib/api";
import { LoadError, ViewLoading } from "@/components/loading";
import { ActionModal, type WindowAction } from "@/components/action-modal";
import { FormView } from "./form-view";
import { ListView } from "./list-view";
import { getFormView, getListView } from "./view-registry";
import { applyViewMetadata } from "./view-metadata";
import type { ActionSchema, RecordsResponse } from "./types";

export default function ActionPage({ actionId, basePath }: { actionId: number; basePath: string }) {
  const location = useLocation();
  const navigate = useNavigate();
  const suffix = location.pathname.slice(basePath.length).replace(/^\//, "");
  const recordId = suffix || undefined;
  const [schema, setSchema] = useState<ActionSchema>();
  const [data, setData] = useState<RecordsResponse>();
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<string[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [editing, setEditing] = useState(recordId === "new");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();
  const [modal, setModal] = useState<WindowAction>();
  const [reload, setReload] = useState(0);
  const onchangeSequence = useRef(0);
  const requestSequence = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    setSchema(undefined); setData(undefined); setError(undefined); setLoading(true); setSelected([]); setFilters([]); setQuery(""); setPage(1);
    api<ActionSchema>(`/api/v1/ui/actions/${actionId}`, { signal: controller.signal }).then((response) => setSchema(applyViewMetadata({ ...response, form: { ...response.form, allFields: response.form.sections.flatMap((section) => section.fields) } }))).catch((reason) => { if (reason.name !== "AbortError") setError(reason.message); }).finally(() => setLoading(false));
    return () => controller.abort();
  }, [actionId]);

  useEffect(() => {
    if (!schema) return;
    const controller = new AbortController();
    const sequence = ++requestSequence.current;
    setLoading(true); setError(undefined);
    if (recordId) {
      setEditing(recordId === "new");
      api<{ id: number | null; values: Record<string, unknown> }>(`/api/v1/ui/actions/${actionId}/records/${recordId}`, { signal: controller.signal }).then((response) => { if (sequence === requestSequence.current) setValues(response.values); }).catch((reason) => { if (reason.name !== "AbortError") setError(reason.message); }).finally(() => { if (sequence === requestSequence.current) setLoading(false); });
    } else {
      const timeout = setTimeout(() => {
        const params = new URLSearchParams({ page: String(page), ...(query ? { q: query } : {}), ...(filters.length ? { filters: filters.join(",") } : {}) });
        api<RecordsResponse>(`/api/v1/ui/actions/${actionId}/records?${params}`, { signal: controller.signal }).then((response) => { if (sequence === requestSequence.current) { setData(response); setSelected([]); } }).catch((reason) => { if (reason.name !== "AbortError") setError(reason.message); }).finally(() => { if (sequence === requestSequence.current) setLoading(false); });
      }, query ? 250 : 0);
      return () => { clearTimeout(timeout); controller.abort(); };
    }
    return () => controller.abort();
  }, [schema, actionId, recordId, page, query, filters, reload]);

  async function save() {
    if (!schema) return;
    setSaving(true); setError(undefined);
    try {
      const response = await apiMutation<{ id: number }>(`/api/v1/ui/actions/${actionId}/records${recordId === "new" ? "" : `/${recordId}`}`, "POST", { values });
      setEditing(false);
      if (recordId === "new") navigate(`${basePath}/${response.id}`, { replace: true }); else setReload((value) => value + 1);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setSaving(false); }
  }

  async function changeField(name: string, value: unknown) {
    const nextValues = { ...values, [name]: value };
    setValues(nextValues);
    if (!schema?.form.onchange[name]) return;
    const sequence = ++onchangeSequence.current;
    try {
      const response = await apiMutation<{ values: Record<string, unknown>; warnings: unknown[] }>(`/api/v1/ui/actions/${actionId}/onchange`, "POST", { values: nextValues, field: name });
      if (sequence === onchangeSequence.current) setValues((current) => ({ ...current, ...response.values }));
    } catch (reason) { if (sequence === onchangeSequence.current) setError(reason instanceof Error ? reason.message : String(reason)); }
  }

  async function runButton(name: string, type: "object" | "action") {
    if (!recordId || recordId === "new") return;
    setLoading(true);
    try { const response = await apiMutation<{ result?: unknown; recordAvailable?: boolean }>(`/api/v1/ui/actions/${actionId}/records/${recordId}/button`, "POST", { name, type }); const result = response.result as WindowAction | undefined; if (result?.type === "ir.actions.act_window" && (result.target === "new" || result.views?.some((view) => view[1] === "form"))) setModal(result); else if (response.recordAvailable === false) navigate(basePath); else setReload((value) => value + 1); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setLoading(false); }
  }

  async function remove() {
    if (!selected.length || !confirm(`Hapus ${selected.length} data terpilih? Tindakan ini tidak dapat dibatalkan.`)) return;
    try { await apiMutation(`/api/v1/ui/actions/${actionId}/records/delete`, "POST", { ids: selected }); setReload((value) => value + 1); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  }

  async function bulkAction(serverActionId: number) {
    try { await apiMutation(`/api/v1/ui/actions/${actionId}/bulk-action`, "POST", { ids: selected, serverActionId }); setReload((value) => value + 1); }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  }

  if (error && !schema) return <LoadError message={error} retry={() => setReload((value) => value + 1)}/>;
  if (!schema) return <ViewLoading/>;
  if (recordId) {
    if (loading && !Object.keys(values).length) return <ViewLoading/>;
    const CustomForm = getFormView(schema) || FormView;
    return <><CustomForm schema={schema} basePath={basePath} id={recordId === "new" ? undefined : Number(recordId)} values={values} editing={editing} saving={saving} onEdit={() => setEditing(true)} onChange={changeField} onSave={save} onButton={runButton}/>{loading && <div className="workspace-form-loading"/>}{modal && <ActionModal action={modal} onClose={() => setModal(undefined)} onDone={() => { setModal(undefined); setReload((value) => value + 1); }}/>} {error && <div className="workspace-toast-error">{error}</div>}</>;
  }
  const CustomList = getListView(schema) || ListView;
  return <><CustomList schema={schema} basePath={basePath} data={data} query={query} page={page} loading={loading} selected={selected} filters={filters} onQuery={(value) => { setQuery(value); setPage(1); }} onPage={setPage} onSelected={setSelected} onFilters={(value) => { setFilters(value); setPage(1); }} onRefresh={() => setReload((value) => value + 1)} onDelete={remove} onBulkAction={bulkAction}/>{error && <div className="workspace-toast-error">{error}</div>}</>;
}
