import type { ViewMetadata } from "./view-metadata";

export interface FieldSchema {
  name: string;
  label: string;
  type: string;
  widget?: string | null;
  relation?: string;
  selection?: [string, string][];
  required?: boolean;
  readonly?: boolean;
  sortable?: boolean;
  currency_field?: string;
  help?: string;
  placeholder?: string;
  options?: Record<string, unknown>;
  parent?: string;
  relationView?: { editable: boolean; columns: FieldSchema[] } | null;
  accept?: string;
  modifiers?: Record<string, unknown>;
}
export interface FormButtonSchema { name: string; label: string; type: "object" | "action"; primary: boolean; modifiers?: Record<string, unknown> }
export interface FilterSchema { name: string; label: string; domain: unknown[] }
export interface BulkActionSchema { id: number; label: string; kind: "action" | "print" }
export interface ActionSchema {
  id: number;
  actionXmlid: string;
  schemaSource: "managed" | "xml";
  name: string;
  model: string;
  limit: number;
  ui?: ViewMetadata;
  list: { id: number | false; title: string; columns: FieldSchema[]; readFields?: string[]; defaultOrder?: string; create: boolean; delete: boolean; export: boolean; filters: FilterSchema[]; actions: BulkActionSchema[] };
  form: { id: number | false; title: string; sections: { id?: string; label: string; description?: string; columns?: 1 | 2 | 3; fields: FieldSchema[] }[]; allFields?: FieldSchema[]; writeFields?: string[]; create: boolean; write: boolean; onchange: Record<string, string>; statusField?: FieldSchema; statusVisible: string[]; buttons: FormButtonSchema[] };
}
export interface RecordsResponse { items: Record<string, unknown>[]; total: number; page: number; pageSize: number }
