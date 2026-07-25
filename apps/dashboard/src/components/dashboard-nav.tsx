import Link from "next/link";

/**
 * The twelve approved user-facing sections — CLAUDE.md section 2. Routes are
 * placeholders until the corresponding roadmap phase implements them; do not
 * add sections beyond this list.
 */
const NAV_SECTIONS = [
  { label: "Dashboard", href: "/" },
  { label: "Customers", href: "/customers" },
  { label: "Leads", href: "/leads" },
  { label: "Orders & Restaurant Operations", href: "/orders" },
  { label: "Menu, Products & Inventory", href: "/menu" },
  { label: "Reservations & Calendar", href: "/reservations" },
  { label: "Communication Hub", href: "/communications" },
  { label: "Lightweight Knowledge Base", href: "/knowledge-base" },
  { label: "Staff & HR", href: "/staff" },
  { label: "Marketing, Loyalty & Feedback", href: "/marketing" },
  { label: "Reports, Analytics & AI Center", href: "/reports" },
  { label: "Integrations, Security & Settings", href: "/settings" },
] as const;

export function DashboardNav() {
  return (
    <nav aria-label="Primary" className="border-r border-black/10 dark:border-white/15 w-64 shrink-0 p-4">
      <p className="px-2 pb-3 text-sm font-semibold tracking-wide text-zinc-500 dark:text-zinc-400">
        RKPR Restaurant CRM
      </p>
      <ul className="flex flex-col gap-1">
        {NAV_SECTIONS.map((section) => (
          <li key={section.href}>
            <Link
              href={section.href}
              className="block rounded-md px-2 py-1.5 text-sm text-zinc-700 hover:bg-zinc-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-900"
            >
              {section.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}
