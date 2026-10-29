import { ArrowLeft, BriefcaseBusiness, Building2, Save, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@toova/components/ui/button";
import { FieldEditor, FieldValue } from "@toova/views/field-registry";
import { modifierActive } from "@toova/views/modifiers";
import type { CustomFormViewProps } from "@toova/views/view-registry";
import type { FieldSchema } from "@toova/views/types";

export default function ContactForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const company = Array.isArray(values.parent_id) ? String(values.parent_id[1]) : "Tanpa perusahaan";
  const field = (name: string, className = "") => {
    const meta = fields[name];
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const readonly = Boolean(meta.readonly) || modifierActive(meta.modifiers, "readonly", values);
    const required = Boolean(meta.required) || modifierActive(meta.modifiers, "required", values);
    return <label className={`toova-customer-field ${className}`} title={meta.help}><span>{meta.label}{required && <b>*</b>}</span><div>{editing && !readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>;
  };
  const section = (title: string, description: string, content: JSX.Element) => <section className="toova-customer-section"><header><h2>{title}</h2><p>{description}</p></header>{content}</section>;
  const image = fields.image_1920 ? <div className="toova-customer-field"><span className="sr-only">Foto</span><div>{editing ? <FieldEditor actionId={schema.id} field={fields.image_1920} value={values.image_1920} onChange={(value) => onChange("image_1920", value)}/> : <FieldValue field={fields.image_1920} value={values.image_1920} record={values}/>}</div></div> : null;

  return <div className="toova-customer toova-contact-profile">
    <header className="toova-customer-header"><div className="toova-customer-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div className="toova-customer-avatar"><UserRound/></div><div><h1>{id ? String(values.name || values.display_name || "Kontak") : "Kontak baru"}</h1><p>{String(values.function || "Jabatan belum diisi")} · {values.active === false ? "Diarsipkan" : "Aktif"}</p></div></div><div className="toova-customer-actions">{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header>
    <main className="toova-customer-body">
      <div className="toova-contact-company"><Building2/><div><span>Terhubung ke</span><strong>{company}</strong><small>Identity perusahaan tetap canonical; PIC tidak menjadi customer atau vendor baru.</small></div></div>
      {section("Profil kontak", "Identitas orang dan posisi pada organisasi terkait.", <div className="toova-customer-overview"><div className="toova-customer-logo">{image}</div><div className="toova-customer-grid">{field("name")}{field("parent_id")}{field("function")}{field("lang")}</div></div>)}
      {section("Informasi kontak", "Kanal komunikasi langsung untuk aktivitas sales, purchasing, atau operasional.", <div className="toova-customer-grid">{field("email")}{field("mobile")}{field("phone")}</div>)}
      {section("Catatan internal", "Konteks relasi, tanggung jawab, atau preferensi komunikasi.", <div className="toova-contact-notes"><BriefcaseBusiness/>{field("comment", "wide")}</div>)}
    </main>
  </div>;
}
