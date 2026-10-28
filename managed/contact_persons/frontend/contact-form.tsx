import { ArrowLeft, BriefcaseBusiness, Building2, Save, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@luma/components/ui/button";
import { FieldEditor, FieldValue } from "@luma/views/field-registry";
import { modifierActive } from "@luma/views/modifiers";
import type { CustomFormViewProps } from "@luma/views/view-registry";
import type { FieldSchema } from "@luma/views/types";

export default function ContactForm({ schema, basePath, id, values, editing, saving, onEdit, onChange, onSave }: CustomFormViewProps) {
  const fields = Object.fromEntries((schema.form.allFields || []).map((field) => [field.name, field])) as Record<string, FieldSchema>;
  const company = Array.isArray(values.parent_id) ? String(values.parent_id[1]) : "Tanpa perusahaan";
  const field = (name: string, className = "") => {
    const meta = fields[name];
    if (!meta || modifierActive(meta.modifiers, "invisible", values)) return null;
    const readonly = Boolean(meta.readonly) || modifierActive(meta.modifiers, "readonly", values);
    const required = Boolean(meta.required) || modifierActive(meta.modifiers, "required", values);
    return <label className={`luma-customer-field ${className}`} title={meta.help}><span>{meta.label}{required && <b>*</b>}</span><div>{editing && !readonly ? <FieldEditor actionId={schema.id} field={meta} value={values[name]} parentValues={values} onChange={(value) => onChange(name, value)}/> : <FieldValue field={meta} value={values[name]} record={values}/>}</div></label>;
  };
  const section = (title: string, description: string, content: JSX.Element) => <section className="luma-customer-section"><header><h2>{title}</h2><p>{description}</p></header>{content}</section>;
  const image = fields.image_1920 ? <div className="luma-customer-field"><span className="sr-only">Foto</span><div>{editing ? <FieldEditor actionId={schema.id} field={fields.image_1920} value={values.image_1920} onChange={(value) => onChange("image_1920", value)}/> : <FieldValue field={fields.image_1920} value={values.image_1920} record={values}/>}</div></div> : null;

  return <div className="luma-customer luma-contact-profile">
    <header className="luma-customer-header"><div className="luma-customer-title"><Button asChild variant="ghost" size="icon"><Link to={basePath}><ArrowLeft className="h-3.5 w-3.5"/></Link></Button><div className="luma-customer-avatar"><UserRound/></div><div><span>Kontak/PIC</span><h1>{id ? String(values.name || values.display_name || "Kontak") : "Kontak baru"}</h1><p>{String(values.function || "Jabatan belum diisi")} · {values.active === false ? "Diarsipkan" : "Aktif"}</p></div></div><div className="luma-customer-actions">{(id ? schema.form.write : schema.form.create) && (editing ? <Button onClick={onSave} disabled={saving}><Save className="h-3.5 w-3.5"/>{saving ? "Menyimpan..." : "Simpan"}</Button> : <Button variant="outline" onClick={onEdit}>Edit</Button>)}</div></header>
    <main className="luma-customer-body">
      <div className="luma-contact-company"><Building2/><div><span>Terhubung ke</span><strong>{company}</strong><small>Identity perusahaan tetap canonical; PIC tidak menjadi customer atau vendor baru.</small></div></div>
      {section("Profil kontak", "Identitas orang dan posisi pada organisasi terkait.", <div className="luma-customer-overview"><div className="luma-customer-logo">{image}</div><div className="luma-customer-grid">{field("name")}{field("parent_id")}{field("function")}{field("lang")}</div></div>)}
      {section("Informasi kontak", "Kanal komunikasi langsung untuk aktivitas sales, purchasing, atau operasional.", <div className="luma-customer-grid">{field("email")}{field("mobile")}{field("phone")}</div>)}
      {section("Catatan internal", "Konteks relasi, tanggung jawab, atau preferensi komunikasi.", <div className="luma-contact-notes"><BriefcaseBusiness/>{field("comment", "wide")}</div>)}
    </main>
  </div>;
}
