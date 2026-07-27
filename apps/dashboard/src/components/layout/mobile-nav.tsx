"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useCurrentUser } from "@/lib/hooks/use-current-user";
import { NAV_SECTIONS, isNavSectionVisible } from "./nav-config";

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Off-canvas navigation for small screens — desktop uses Sidebar instead;
 * both read the same NAV_SECTIONS source so they never drift apart. */
export function MobileNav() {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const [open, setOpen] = useState(false);

  const sections = NAV_SECTIONS.filter((section) => isNavSectionVisible(section, user));

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open navigation">
          <Menu className="size-5" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-72 p-0">
        <SheetHeader className="border-b">
          <SheetTitle>RKPR Restaurant CRM</SheetTitle>
        </SheetHeader>
        <nav aria-label="Primary" className="flex flex-col gap-1 overflow-y-auto p-2">
          {sections.map((section) => {
            const Icon = section.icon;
            const active = isActive(pathname, section.href);
            return (
              <Link
                key={section.href}
                href={section.href}
                onClick={() => setOpen(false)}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-foreground/80 hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <Icon className="size-4 shrink-0" aria-hidden="true" />
                {section.label}
              </Link>
            );
          })}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
