import type { ReactNode } from "react";
import { DocumentBack } from "@/components/document-relations";

export interface ManagedFormTab<T extends string = string> { key: T; label: string; count?: number }

export function ManagedFormShell<T extends string>({ icon, title, subtitle, badge, actions, tabs, activeTab, onTabChange, onBack, children, className = "" }: {
  icon: ReactNode; title: ReactNode; subtitle?: ReactNode; badge?: ReactNode; actions?: ReactNode;
  tabs?: ManagedFormTab<T>[]; activeTab?: T; onTabChange?: (tab: T) => void;
  onBack: () => void; children: ReactNode; className?: string;
}) {
  return <div className={`managed-form ${className}`}>
    <header className="managed-form-header"><div className="managed-form-title"><DocumentBack onBack={onBack}/><div className="managed-form-mark">{icon}</div><div><div className="managed-form-heading"><h1>{title}</h1>{badge}</div>{subtitle && <p>{subtitle}</p>}</div></div><div className="managed-form-actions">{actions}</div></header>
    {tabs?.length ? <nav className="managed-form-tabs" aria-label="Bagian formulir">{tabs.map((tab) => <button key={tab.key} type="button" className={activeTab === tab.key ? "active" : undefined} aria-current={activeTab === tab.key ? "page" : undefined} onClick={() => onTabChange?.(tab.key)}>{tab.label}{tab.count !== undefined && <i>{tab.count}</i>}</button>)}</nav> : null}
    <main className="managed-form-body">{children}</main>
  </div>;
}

export function ManagedFormSection({ title, description, children, className = "" }: { title: ReactNode; description?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`managed-form-section ${className}`}><header><h2>{title}</h2>{description && <p>{description}</p>}</header>{children}</section>;
}
