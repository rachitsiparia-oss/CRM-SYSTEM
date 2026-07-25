import { DashboardNav } from "@/components/dashboard-nav";
import { UserMenu } from "@/components/user-menu";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1">
      <DashboardNav />
      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-end border-b border-black/10 px-6 py-3 dark:border-white/15">
          <UserMenu />
        </header>
        <main className="flex flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
}
