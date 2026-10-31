import { FileText, Save } from "lucide-react";
import { useEffect, useState, type CSSProperties } from "react";
import { DocumentRelations } from "@/components/document-relations";
import { ManagedFormSection, ManagedFormShell } from "@/components/managed-form";
import { Button } from "@/components/ui/button";
import { DateRangePicker } from "@/components/ui/date-range-picker";
import { FieldEditor, FieldValue } from "./field-registry";
import { modifierActive } from "./modifiers";
import type { CustomFormViewProps } from "./view-registry";

export function FormView({ schema, id, values, relatedDocuments, editing, saving, onEdit, onChange, onSave, onButton, onBack }: CustomFormViewProps) {
  const sections = schema.form.sections.filter((section) => section.fields.some((field) => !modifierActive(field.modifiers, "invisible", values)));
  const [activeSection, setActiveSection] = useState("0");
  useEffect(() => { if (Number(activeSection) >= sections.length) setActiveSection("0"); }, [activeSection, sections.length]);
  const section = sections[Number(activeSection)] || sections[0];
  const canWrite = id ? schema.form.write : schema.form.create;
  const status = schema.form.statusField;
  const stateLabel = status?.selection?.find(([key]) => key === values[status.name])?.[1];
  const buttons = id ? schema.form.buttons.filter((button) => !modifierActive(button.modifiers, "invisible", values)) : [];
  const actions = <><DocumentRelations groups={relatedDocuments}/>{buttons.map((button) => <Button key={`${button.type}:${button.name}:${button.label}`} variant={button.primary ? "default" : "outline"} onClick={() => onButton(button.name, button.type)}>{button.label}</Button>)}{canWrite && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</>;
  const badge = stateLabel ? <span className="managed-form-badge">{stateLabel}</span> : undefined;
  const tabs = sections.length > 1 ? sections.map((item, index) => ({ key: String(index), label: item.label })) : undefined;
  return <ManagedFormShell icon={<FileText/>} title={id ? String(values.display_name || values.name || schema.form.title) : `Baru — ${schema.form.title}`} subtitle={schema.name} badge={badge} actions={actions} tabs={tabs} activeTab={activeSection} onTabChange={setActiveSection} onBack={onBack}>
    {section && <ManagedFormSection title={section.label} description={section.description}><div className="workspace-form-grid" style={{ "--form-columns": section.columns || 3 } as CSSProperties}>{section.fields.filter((field) => field.name !== status?.name && !modifierActive(field.modifiers, "invisible", values) && !(field.widget === "daterange" && field.options?.related_start_date)).map((field) => { const readonly = Boolean(field.readonly) || modifierActive(field.modifiers, "readonly", values); const required = Boolean(field.required) || modifierActive(field.modifiers, "required", values); const rangeEnd = field.widget === "daterange" && typeof field.options?.related_end_date === "string" ? field.options.related_end_date : undefined; return <label key={field.name} title={field.help} className={["text", "html", "one2many", "many2many"].includes(field.type) ? "workspace-form-wide" : undefined}><span>{field.label}{required && <b>*</b>}</span><div className="workspace-form-control">{editing && !readonly ? rangeEnd ? <DateRangePicker from={values[field.name] ? String(values[field.name]) : false} to={values[rangeEnd] ? String(values[rangeEnd]) : false} onChange={(range) => { onChange(field.name, range.from); onChange(rangeEnd, range.to); }}/> : <FieldEditor actionId={schema.id} field={field} value={values[field.name]} parentValues={values} onChange={(value) => onChange(field.name, value)}/> : rangeEnd ? <span>{values[field.name] ? new Date(`${values[field.name]}T00:00:00`).toLocaleDateString("id-ID") : "—"} – {values[rangeEnd] ? new Date(`${values[rangeEnd]}T00:00:00`).toLocaleDateString("id-ID") : "—"}</span> : <FieldValue field={field} value={values[field.name]} record={values}/>}</div></label>; })}</div></ManagedFormSection>}
  </ManagedFormShell>;
}
