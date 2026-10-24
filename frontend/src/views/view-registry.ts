import type { ComponentType } from "react";
import type { ActionSchema, RecordsResponse } from "./types";

export interface CustomListViewProps {
  schema: ActionSchema;
  basePath: string;
  data?: RecordsResponse;
  query: string;
  page: number;
  loading: boolean;
  selected: number[];
  filters: string[];
  onQuery: (value: string) => void;
  onPage: (value: number) => void;
  onSelected: (value: number[]) => void;
  onFilters: (value: string[]) => void;
  onRefresh: () => void;
  onDelete: () => void;
  onBulkAction: (id: number) => void;
}
export interface CustomFormViewProps {
  schema: ActionSchema;
  basePath: string;
  id?: number;
  values: Record<string, unknown>;
  editing: boolean;
  saving: boolean;
  onEdit: () => void;
  onChange: (name: string, value: unknown) => void;
  onSave: () => void;
  onButton: (name: string, type: "object" | "action") => void;
}

const modelListViews = new Map<string, ComponentType<CustomListViewProps>>();
const modelFormViews = new Map<string, ComponentType<CustomFormViewProps>>();
const actionListViews = new Map<string, ComponentType<CustomListViewProps>>();
const actionFormViews = new Map<string, ComponentType<CustomFormViewProps>>();

export function registerModelListView(model: string, component: ComponentType<CustomListViewProps>) { modelListViews.set(model, component); }
export function registerModelFormView(model: string, component: ComponentType<CustomFormViewProps>) { modelFormViews.set(model, component); }
export function registerActionListView(actionXmlid: string, component: ComponentType<CustomListViewProps>) { actionListViews.set(actionXmlid, component); }
export function registerActionFormView(actionXmlid: string, component: ComponentType<CustomFormViewProps>) { actionFormViews.set(actionXmlid, component); }
export function getListView(schema: ActionSchema) { return actionListViews.get(schema.actionXmlid) || modelListViews.get(schema.model); }
export function getFormView(schema: ActionSchema) { return actionFormViews.get(schema.actionXmlid) || modelFormViews.get(schema.model); }
