import { UserMenu } from "@/components/user-menu";
import { Breadcrumbs } from "./breadcrumbs";
import { GlobalSearch } from "./global-search";
import { MobileNav } from "./mobile-nav";
import { NotificationsMenu } from "./notifications-menu";

/** Reusable top header — every future page gets this for free through the
 * (app) layout; pages never render their own header. */
export function Header() {
  return (
    <header className="border-border bg-background flex h-14 shrink-0 items-center gap-3 border-b px-4">
      <MobileNav />
      <div className="flex-1">
        <Breadcrumbs />
      </div>
      <div className="hidden flex-1 justify-center md:flex">
        <GlobalSearch />
      </div>
      <div className="flex flex-1 items-center justify-end gap-1">
        <NotificationsMenu />
        <UserMenu />
      </div>
    </header>
  );
}
