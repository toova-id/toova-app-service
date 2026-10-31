import { BriefcaseBusiness, Building2, Save, UserRound } from "lucide-react";
import { Button } from "@toova/components/ui/button";
import { ManagedFormSection, ManagedFormShell } from "@toova/components/managed-form";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import { modifierActive } from "@toova/views/modifiers";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

export default function ContactForm({ schema, id, values, editing, saving, onEdit, onChange, onSave, onBack }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const company = Array.isArray(values.parent_id) ? String(values.parent_id[1]) : "Tanpa perusahaan";
  const field = (name: string, className = "") => {
    const meta = fields[name];
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const readonly = Boolean(meta.readonly) || modifierActive(meta.modifiers, "readonly", values);
    const required = Boolean(meta.required) || modifierActive(meta.modifiers, "required", values);
    return <label className={`managed-form-field ${className}`} title={meta.help}><span>{meta.label}{required && <b>*</b>}</span><div>{editing && !readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>;
  };
  const section = (title: string, description: string, content: JSX.Element) => <ManagedFormSection title={title} description={description}>{content}</ManagedFormSection>;
  const image = fields.image_1920 ? <div className="managed-form-field"><span className="sr-only">Foto</span><div>{editing ? <FieldEditor actionId={schema.id} field={fields.image_1920} value={values.image_1920} onChange={(value) => onChange("image_1920", value)}/> : <FieldValue field={fields.image_1920} value={values.image_1920} record={values}/>}</div></div> : null;

  const actions = (id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>);
  return <ManagedFormShell icon={<UserRound/>} title={id ? String(values.name || values.display_name || "Kontak") : "Kontak baru"} subtitle={`${String(values.function || "Jabatan belum diisi")} · ${values.active === false ? "Diarsipkan" : "Aktif"}`} actions={actions} onBack={onBack} className="toova-customer toova-contact-profile">
      <div className="toova-contact-company"><Building2/><div><span>Terhubung ke</span><strong>{company}</strong><small>Identity perusahaan tetap canonical; PIC tidak menjadi customer atau vendor baru.</small></div></div>
      {section("Profil kontak", "Identitas orang dan posisi pada organisasi terkait.", <div className="toova-customer-overview"><div className="toova-customer-logo">{image}</div><div className="managed-form-grid">{field("name")}{field("parent_id")}{field("function")}{field("lang")}</div></div>)}
      {section("Informasi kontak", "Kanal komunikasi langsung untuk aktivitas sales, purchasing, atau operasional.", <div className="managed-form-grid">{field("email")}{field("mobile")}{field("phone")}</div>)}
      {section("Catatan internal", "Konteks relasi, tanggung jawab, atau preferensi komunikasi.", <div className="toova-contact-notes"><BriefcaseBusiness/>{field("comment", "wide")}</div>)}
  </ManagedFormShell>;
}
