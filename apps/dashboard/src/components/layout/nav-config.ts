import {
  LayoutDashboard,
  Users,
  UserPlus,
  ShoppingCart,
  UtensilsCrossed,
  CalendarDays,
  MessageSquare,
  BookOpen,
  UsersRound,
  Megaphone,
  BarChart3,
  Settings,
  type LucideIcon,
} from "lucide-react";
import type { CurrentUser } from "@rkpr/contracts";
import { hasPermission } from "@/lib/hooks/use-current-user";

export interface NavChild {
  label: string;
  href: string;
}

export interface NavSection {
  label: string;
  href: string;
  icon: LucideIcon;
  /** A single permission code, or a list checked with OR semantics — used
   * by "Menu, Products & Inventory" (CLAUDE.md section 2's section 5 bundles
   * both domains under one nav entry) so a staff member with only
   * `inventory.view` still sees the section without also needing
   * `menu.view`. */
  requiredPermission?: string | string[];
  children?: NavChild[];
}

/**
 * The twelve approved user-facing sections — CLAUDE.md section 2. Do not
 * add sections beyond this list; do not invent nested items for modules
 * that don't have real sub-routes yet. `requiredPermission` is set only
 * where a real backend permission gates the route today (Staff & HR
 * Phase 3, Menu Phase 6, Orders Phase 7) — the remaining placeholder
 * shells have no authorization of their own yet, so hiding them on a
 * made-up permission would be a hardcoded assumption
 * (ARCHITECTURE_AND_TECH_STACK.md 6.9).
 */
export const NAV_SECTIONS: NavSection[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Customers", href: "/customers", icon: Users },
  { label: "Leads", href: "/leads", icon: UserPlus },
  {
    label: "Orders & Restaurant Operations",
    href: "/orders",
    icon: ShoppingCart,
    requiredPermission: "orders.view",
    children: [
      { label: "Dashboard", href: "/orders" },
      { label: "All Orders", href: "/orders/list" },
    ],
  },
  {
    label: "Menu, Products & Inventory",
    href: "/menu",
    icon: UtensilsCrossed,
    requiredPermission: ["menu.view", "inventory.view"],
    children: [
      { label: "Products", href: "/menu" },
      { label: "Categories", href: "/menu/categories" },
      { label: "Modifier Groups", href: "/menu/modifier-groups" },
      { label: "Inventory Dashboard", href: "/inventory" },
      { label: "Inventory Items", href: "/inventory/items" },
      { label: "Recipes", href: "/inventory/recipes" },
      { label: "Suppliers", href: "/inventory/suppliers" },
      { label: "Receipts", href: "/inventory/receipts" },
      { label: "Adjustments & Wastage", href: "/inventory/adjustments" },
      { label: "Transfers", href: "/inventory/transfers" },
      { label: "Stock Counts", href: "/inventory/stock-counts" },
      { label: "Movement Ledger", href: "/inventory/movements" },
    ],
  },
  {
    label: "Reservations & Calendar",
    href: "/reservations",
    icon: CalendarDays,
    requiredPermission: "reservations.view",
    children: [
      { label: "Dashboard", href: "/reservations" },
      { label: "Calendar", href: "/reservations/calendar" },
      { label: "Reservations", href: "/reservations/list" },
      { label: "Tables & Floor", href: "/reservations/tables" },
      { label: "Dining Areas", href: "/reservations/dining-areas" },
      { label: "Waitlist", href: "/reservations/waitlist" },
      { label: "Business Hours", href: "/reservations/business-hours" },
      { label: "Reservation Settings", href: "/reservations/settings" },
    ],
  },
  {
    label: "Communication Hub",
    href: "/communications",
    icon: MessageSquare,
    requiredPermission: "communications.view",
    children: [
      { label: "Dashboard", href: "/communications" },
      { label: "Inbox", href: "/communications/inbox" },
      { label: "Templates", href: "/communications/templates" },
      { label: "Scheduled Messages", href: "/communications/scheduled" },
      { label: "Preferences", href: "/communications/preferences" },
      { label: "Suppression List", href: "/communications/suppressions" },
      { label: "Channels & Providers", href: "/communications/channels" },
      { label: "Call Logs", href: "/communications/call-logs" },
      { label: "Analytics", href: "/communications/analytics" },
      { label: "Tasks", href: "/communications/tasks" },
      { label: "Notifications", href: "/communications/notifications" },
    ],
  },
  { label: "Lightweight Knowledge Base", href: "/knowledge-base", icon: BookOpen },
  {
    label: "Staff & HR",
    href: "/staff",
    icon: UsersRound,
    requiredPermission: "staff.view",
    children: [
      { label: "Directory", href: "/staff" },
      { label: "Roles & Permissions", href: "/staff/roles" },
    ],
  },
  { label: "Marketing, Loyalty & Feedback", href: "/marketing", icon: Megaphone },
  { label: "Reports, Analytics & AI Center", href: "/reports", icon: BarChart3 },
  { label: "Integrations, Security & Settings", href: "/settings", icon: Settings },
];

/** Shared by Sidebar and MobileNav so the two navigation surfaces can never
 * disagree about which sections a signed-in user can see. */
export function isNavSectionVisible(
  section: NavSection,
  user: CurrentUser | undefined,
): boolean {
  if (!section.requiredPermission) return true;
  const codes = Array.isArray(section.requiredPermission)
    ? section.requiredPermission
    : [section.requiredPermission];
  return codes.some((code) => hasPermission(user, code));
}

/** Flat lookup used by breadcrumbs to resolve a pathname segment back to
 * its human label without duplicating the section list. */
export function findNavLabel(pathname: string): string | undefined {
  for (const section of NAV_SECTIONS) {
    if (section.href === pathname) return section.label;
    for (const child of section.children ?? []) {
      if (child.href === pathname) return child.label;
    }
  }
  return undefined;
}
