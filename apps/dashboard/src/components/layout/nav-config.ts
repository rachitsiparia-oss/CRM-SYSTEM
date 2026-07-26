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

export interface NavChild {
  label: string;
  href: string;
}

export interface NavSection {
  label: string;
  href: string;
  icon: LucideIcon;
  requiredPermission?: string;
  children?: NavChild[];
}

/**
 * The twelve approved user-facing sections — CLAUDE.md section 2. Do not
 * add sections beyond this list; do not invent nested items for modules
 * that don't have real sub-routes yet. `requiredPermission` is set only
 * where a real backend permission gates the route today (Staff & HR,
 * Phase 3) — the other eleven are placeholder shells with no
 * authorization of their own yet, so hiding them on a made-up permission
 * would be a hardcoded assumption (ARCHITECTURE_AND_TECH_STACK.md 6.9).
 */
export const NAV_SECTIONS: NavSection[] = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Customers", href: "/customers", icon: Users },
  { label: "Leads", href: "/leads", icon: UserPlus },
  { label: "Orders & Restaurant Operations", href: "/orders", icon: ShoppingCart },
  {
    label: "Menu, Products & Inventory",
    href: "/menu",
    icon: UtensilsCrossed,
    requiredPermission: "menu.view",
    children: [
      { label: "Products", href: "/menu" },
      { label: "Categories", href: "/menu/categories" },
      { label: "Modifier Groups", href: "/menu/modifier-groups" },
    ],
  },
  { label: "Reservations & Calendar", href: "/reservations", icon: CalendarDays },
  { label: "Communication Hub", href: "/communications", icon: MessageSquare },
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
