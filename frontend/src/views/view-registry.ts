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

const listViews = new Map<string, ComponentType<CustomListViewProps>>();
const formViews = new Map<string, ComponentType<CustomFormViewProps>>();

export function registerModelListView(model: string, component: ComponentType<CustomListViewProps>) { listViews.set(model, component); }
export function registerModelFormView(model: string, component: ComponentType<CustomFormViewProps>) { formViews.set(model, component); }
export function getModelListView(model: string) { return listViews.get(model); }
export function getModelFormView(model: string) { return formViews.get(model); }
