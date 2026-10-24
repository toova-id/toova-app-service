import type { ActionSchema, FieldSchema } from "./types";

export interface ViewFieldMetadata { name: string; label?: string; widget?: string }
export type ViewFieldReference = string | ViewFieldMetadata;
export interface FormSectionMetadata { id: string; label: string; description?: string; columns?: 1 | 2 | 3; fields: ViewFieldReference[] }
export interface ViewMetadata {
  list?: { columns?: ViewFieldReference[] };
  form?: { titleField?: string; sections?: FormSectionMetadata[] };
}

const actionViews = new Map<string, ViewMetadata>();
const modelViews = new Map<string, ViewMetadata>();

export function registerActionView(actionXmlid: string, metadata: ViewMetadata) { actionViews.set(actionXmlid, metadata); }
export function registerModelView(model: string, metadata: ViewMetadata) { modelViews.set(model, metadata); }

function merge(base?: ViewMetadata, override?: ViewMetadata): ViewMetadata | undefined {
  if (!base) return override;
  if (!override) return base;
  return { list: { ...base.list, ...override.list }, form: { ...base.form, ...override.form } };
}

export function getViewMetadata(schema: ActionSchema) { return merge(modelViews.get(schema.model), actionViews.get(schema.actionXmlid)); }

function applyField(reference: ViewFieldReference, fields: Map<string, FieldSchema>): FieldSchema | undefined {
  const config = typeof reference === "string" ? { name: reference } : reference;
  const field = fields.get(config.name);
  return field ? { ...field, ...(config.label ? { label: config.label } : {}), ...(config.widget ? { widget: config.widget } : {}) } : undefined;
}

export function applyViewMetadata(schema: ActionSchema): ActionSchema {
  const metadata = getViewMetadata(schema);
  if (!metadata) return schema;
  const listFields = new Map(schema.list.columns.map((field) => [field.name, field]));
  const allFormFields = schema.form.allFields || schema.form.sections.flatMap((section) => section.fields);
  const formFields = new Map(allFormFields.map((field) => [field.name, field]));
  const columns = metadata.list?.columns?.map((field) => applyField(field, listFields)).filter((field): field is FieldSchema => Boolean(field)) ?? schema.list.columns;
  const sections = metadata.form?.sections?.map((section) => ({
    id: section.id,
    label: section.label,
    description: section.description,
    columns: section.columns,
    fields: section.fields.map((field) => applyField(field, formFields)).filter((field): field is FieldSchema => Boolean(field)),
  })).filter((section) => section.fields.length) ?? schema.form.sections;
  return { ...schema, ui: metadata, list: { ...schema.list, columns }, form: { ...schema.form, allFields: allFormFields, sections } };
}
