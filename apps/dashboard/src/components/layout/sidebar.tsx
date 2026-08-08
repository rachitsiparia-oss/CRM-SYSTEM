"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown, ChevronsLeft, ChevronsRight, Search, UtensilsCrossed } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { UserMenu } from "@/components/user-menu";
import { useCurrentUser } from "@/lib/hooks/use-current-user";
import { NAV_SECTIONS, isNavSectionVisible } from "./nav-config";

const COLLAPSE_STORAGE_KEY = "rkpr:sidebar-collapsed";

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const [collapsed, setCollapsed] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const [query, setQuery] = useState("");

  useEffect(() => {
    // Mount-only read of a persisted UI preference — deliberately not
    // read during the initial render (via a lazy useState initializer)
    // because localStorage isn't available during SSR; reading it there
    // would make the server and first client render disagree and trigger
    // a hydration-mismatch warning. The one-frame "flash of expanded"
    // this trades for is the standard, accepted cost of that fix.
    const stored = window.localStorage.getItem(COLLAPSE_STORAGE_KEY);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (stored === "1") setCollapsed(true);
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      window.localStorage.setItem(COLLAPSE_STORAGE_KEY, next ? "1" : "0");
      return next;
    });
  }

  const visibleSections = useMemo(
    () => NAV_SECTIONS.filter((section) => isNavSectionVisible(section, user)),
    [user],
  );

  // Client-side filter over an already-permission-scoped nav list — matches
  // a section's own label or any of its children's labels. Purely a
  // navigation aid (find a buried sub-route fast), not a substitute for the
  // real cross-module GlobalSearch in the header.
  const normalizedQuery = query.trim().toLowerCase();
  const sections = useMemo(() => {
    if (!normalizedQuery) return visibleSections;
    return visibleSections.filter(
      (section) =>
        section.label.toLowerCase().includes(normalizedQuery) ||
        section.children?.some((child) => child.label.toLowerCase().includes(normalizedQuery)),
    );
  }, [visibleSections, normalizedQuery]);

  return (
    <nav
      aria-label="Primary"
      className={cn(
        "flex h-full flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 ease-in-out",
        collapsed ? "w-16" : "w-64",
        className,
      )}
    >
      <div className="flex h-16 items-center justify-between gap-2 border-b border-sidebar-border px-3">
        {!collapsed && (
          // A plain (non-link) block, not a second "/" link — the
          // "Dashboard" nav item below already covers that destination, and
          // sidebar.test.tsx asserts exact <a> counts inside this <nav>.
          <div className="flex min-w-0 items-center gap-2 px-1">
            <span className="bg-brand-yellow text-brand-yellow-foreground flex size-8 shrink-0 items-center justify-center rounded-lg">
              <UtensilsCrossed className="size-4" aria-hidden="true" />
            </span>
            <span className="min-w-0 truncate text-sm font-semibold tracking-wide">
              RKPR Restaurant CRM
            </span>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0"
          onClick={toggleCollapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronsRight className="size-4" /> : <ChevronsLeft className="size-4" />}
        </Button>
      </div>

      {!collapsed && (
        <div className="border-b border-sidebar-border p-2">
          <div className="relative">
            <Search
              className="text-muted-foreground pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2"
              aria-hidden="true"
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search navigation…"
              aria-label="Filter navigation"
              className="bg-surface-canvas h-8 border-none pl-8 text-sm shadow-none"
            />
          </div>
        </div>
      )}

      <ul className="flex flex-1 flex-col gap-1 overflow-y-auto p-2">
        {sections.map((section) => {
          const Icon = section.icon;
          const active = isActive(pathname, section.href);
          const hasChildren = !!section.children?.length;
          const groupOpen = openGroups[section.href] ?? active;

          const linkContent = (
            <Link
              href={section.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "relative flex flex-1 items-center gap-3 rounded-md px-2.5 py-2 text-sm font-medium outline-none transition-colors",
                "focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground before:absolute before:top-1 before:bottom-1 before:left-0 before:w-0.5 before:rounded-full before:bg-primary"
                  : "text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
              )}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              {!collapsed && <span className="truncate">{section.label}</span>}
            </Link>
          );

          return (
            <li key={section.href}>
              <div className="flex items-center">
                {collapsed ? (
                  <Tooltip>
                    <TooltipTrigger asChild>{linkContent}</TooltipTrigger>
                    <TooltipContent side="right">{section.label}</TooltipContent>
                  </Tooltip>
                ) : (
                  linkContent
                )}
                {hasChildren && !collapsed && (
                  <button
                    type="button"
                    aria-expanded={groupOpen}
                    aria-label={`Toggle ${section.label} submenu`}
                    className="rounded-md p-2 text-sidebar-foreground/60 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                    onClick={() =>
                      setOpenGroups((prev) => ({ ...prev, [section.href]: !groupOpen }))
                    }
                  >
                    <ChevronDown
                      className={cn("size-4 transition-transform", groupOpen && "rotate-180")}
                    />
                  </button>
                )}
              </div>

              {hasChildren && !collapsed && groupOpen && (
                <ul className="ml-6 mt-1 flex flex-col gap-1 border-l border-sidebar-border pl-3">
                  {section.children!.map((child) => {
                    const childActive = pathname === child.href;
                    return (
                      <li key={child.href}>
                        <Link
                          href={child.href}
                          aria-current={childActive ? "page" : undefined}
                          className={cn(
                            "block rounded-md px-2.5 py-1.5 text-sm outline-none transition-colors",
                            "focus-visible:ring-2 focus-visible:ring-sidebar-ring",
                            childActive
                              ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium"
                              : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                          )}
                        >
                          {child.label}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          );
        })}
      </ul>

      <div className="border-t border-sidebar-border p-2">
        {collapsed ? (
          <div className="flex justify-center">
            <UserMenu variant="compact" />
          </div>
        ) : (
          <UserMenu variant="sidebar" />
        )}
      </div>
    </nav>
  );
}
