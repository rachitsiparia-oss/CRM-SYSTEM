import { UserMenu } from "@/components/user-menu";
import { Breadcrumbs } from "./breadcrumbs";
import { GlobalSearch } from "./global-search";
import { MobileNav } from "./mobile-nav";
import { NotificationsMenu } from "./notifications-menu";
import { ThemeToggle } from "./theme-toggle";

/** Reusable top toolbar — every future page gets this for free through the
 * (app) layout; pages never render their own header. Phase 17.5: the
 * account menu now lives in the Sidebar footer on desktop, so it's hidden
 * here at md+ — but the Sidebar itself is `hidden md:block` (mobile uses
 * MobileNav's sheet instead, which has no account-menu of its own), so a
 * mobile-only copy stays here or mobile users would lose their only way to
 * sign out. */
export function Header() {
  return (
    <header className="border-border bg-card flex h-16 shrink-0 items-center gap-3 border-b px-4">
      <MobileNav />
      <div className="flex-1">
        <Breadcrumbs />
      </div>
      <div className="hidden flex-1 justify-center md:flex">
        <GlobalSearch />
      </div>
      <div className="flex flex-1 items-center justify-end gap-2">
        <ThemeToggle />
        <NotificationsMenu />
        <div className="md:hidden">
          <UserMenu variant="compact" />
        </div>
      </div>
    </header>
  );
}
