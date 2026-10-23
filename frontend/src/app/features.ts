import { lazy } from "react";
import { BarChart3, Boxes, Building2, Factory, HandCoins, LayoutDashboard, PackageCheck, ShoppingCart, Users } from "lucide-react";
import type { FeatureRoute, NavigationItem } from "./types";

export const navigation: NavigationItem[] = [
  { label: "Beranda", path: "/app", icon: LayoutDashboard },
  { label: "Penjualan", path: "/app/sales", icon: HandCoins, module: "sale" },
  { label: "Pembelian", path: "/app/purchases", icon: ShoppingCart, module: "purchase" },
  { label: "Persediaan", path: "/app/inventory", icon: Boxes, module: "stock" },
  { label: "Keuangan", path: "/app/finance", icon: BarChart3, module: "account" },
  { label: "Karyawan", path: "/app/people", icon: Users, module: "hr" },
  { label: "Produksi", path: "/app/manufacturing", icon: Factory, module: "mrp" },
  { label: "Perusahaan", path: "/app/company", icon: Building2 },
];

export const routes: FeatureRoute[] = [
  { path: "/app", component: lazy(() => import("@/features/dashboard/dashboard-page")) },
  { path: "/app/*", component: lazy(() => import("@/features/menu-route-page")) },
  { path: "*", component: lazy(() => import("@/features/not-found-page")) },
];

export const placeholderIcons = { purchase: ShoppingCart, stock: PackageCheck };
