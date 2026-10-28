import type { ComponentType } from "react";

export interface SettingsReadiness { status: "ready" | "warning" | "error"; message?: string }
export interface SettingsSection { key: string; placement: "main" | "advanced"; label: string; description?: string; icon?: string; sequence: number; permission: string; action_xmlid?: string; actionId?: number | null; provider?: string; level: "none" | "read" | "write"; readiness: SettingsReadiness }
export interface PermissionItem { key: string; label: string; level?: "none" | "read" | "write" }
export interface PermissionFeature { key: string; label: string; sequence: number; permissions: PermissionItem[] }
export interface SettingsSectionProps { section: SettingsSection; onBack: () => void }

const sections = new Map<string, ComponentType<SettingsSectionProps>>();
export function registerSettingsSection(key: string, component: ComponentType<SettingsSectionProps>) { sections.set(key, component); }
export function getSettingsSection(key: string) { return sections.get(key); }
