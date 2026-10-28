import { Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api, apiMutation } from "@toova/lib/api";
import { Button } from "@toova/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@toova/components/ui/select";
import type { SettingsSectionProps } from "@toova/features/settings/settings-registry";

export default function ProductSettings({ section }: SettingsSectionProps) {
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);
  useEffect(() => { api<{ values: Record<string, unknown> }>("/api/v1/settings/products").then((result) => setValues(result.values)); }, []);
  const save = async () => { setSaving(true); try { const result = await apiMutation<{ values: Record<string, unknown> }>("/api/v1/settings/products", "POST", { values }); setValues(result.values); } finally { setSaving(false); } };
  return <div className="toova-settings-provider">{section.level === "write" && <div className="toova-settings-provider-actions"><span/><Button onClick={save} disabled={saving}><Save/>{saving ? "Menyimpan..." : "Simpan"}</Button></div>}<section><header><h2>Katalog</h2></header><div className="toova-settings-options"><label><span>Kebijakan invoice</span><Select value={String(values.invoicePolicy || "order")} disabled={section.level !== "write"} onValueChange={(value) => setValues((current) => ({ ...current, invoicePolicy: value }))}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent><SelectItem value="order">Kuantitas dipesan</SelectItem><SelectItem value="delivery">Kuantitas dikirim</SelectItem></SelectContent></Select></label></div></section></div>;
}
