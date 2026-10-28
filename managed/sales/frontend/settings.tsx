import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api, apiMutation } from "@toova/lib/api";
import { Button } from "@toova/components/ui/button";
import { Input } from "@toova/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@toova/components/ui/select";
import { Switch } from "@toova/components/ui/switch";
import type { SettingsSectionProps } from "@toova/features/settings/settings-registry";

export default function SalesSettings({ section }: SettingsSectionProps) {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string>();
  useEffect(() => { api<{ values: Record<string, unknown> }>("/api/v1/settings/sales").then((result) => setValues(result.values)).catch((reason) => setError(reason.message)); }, []);
  const change = (name: string, value: unknown) => setValues((current) => ({ ...current, [name]: value }));
  const save = async () => { setSaving(true); setError(undefined); try { const result = await apiMutation<{ values: Record<string, unknown> }>("/api/v1/settings/sales", "POST", { values }); setValues(result.values); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } finally { setSaving(false); } };
  return <div className="toova-settings-provider">{section.level === "write" && <div className="toova-settings-provider-actions"><span/><Button onClick={save} disabled={saving}><Save/>{saving ? "Menyimpan..." : "Simpan"}</Button></div>}{error && <div className="workspace-toast-error">{error}</div>}<section><header><h2>Penawaran</h2></header><div className="toova-settings-options"><label><span>Masa berlaku</span><div className="flex items-center gap-2"><Switch checked={Boolean(values.use_quotation_validity_days)} disabled={section.level !== "write"} onChange={(event) => change("use_quotation_validity_days", event.target.checked)}/><Input type="number" min={1} value={Number(values.quotation_validity_days || 0)} disabled={section.level !== "write" || !values.use_quotation_validity_days} onChange={(event) => change("quotation_validity_days", Number(event.target.value))}/><small>hari</small></div></label><label><span>Tanda tangan online</span><Switch checked={Boolean(values.portal_confirmation_sign)} disabled={section.level !== "write"} onChange={(event) => change("portal_confirmation_sign", event.target.checked)}/></label><label><span>Pembayaran online</span><Switch checked={Boolean(values.portal_confirmation_pay)} disabled={section.level !== "write"} onChange={(event) => change("portal_confirmation_pay", event.target.checked)}/></label></div></section><section><header><h2>Pesanan & Penagihan</h2></header><div className="toova-settings-options"><label><span>Kebijakan invoice</span><Select value={String(values.default_invoice_policy || "order")} disabled={section.level !== "write"} onValueChange={(value) => change("default_invoice_policy", value)}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="order">Kuantitas dipesan</SelectItem><SelectItem value="delivery">Kuantitas dikirim</SelectItem></SelectContent></Select></label><label><span>Kunci setelah konfirmasi</span><Switch checked={Boolean(values.group_auto_done_setting)} disabled={section.level !== "write"} onChange={(event) => change("group_auto_done_setting", event.target.checked)}/></label></div></section></div>;
}
