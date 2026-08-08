import type { ReactNode } from "react";

import { TooltipProvider } from "@/components/ui/tooltip";
import { Header } from "./header";
import { Sidebar } from "./sidebar";

/** The authenticated shell: sidebar + header + scrollable content area.
 * Every dashboard page renders inside this exactly once, via the (app)
 * route group's layout — no page should build its own sidebar/header.
 * TooltipProvider lives here once for the whole shell (collapsed-sidebar
 * icon tooltips today, any future tooltip usage without re-wrapping). */
export function DashboardShell({ children }: { children: ReactNode }) {
  return (
    <TooltipProvider>
      <div className="flex h-screen w-full overflow-hidden">
        <div className="hidden md:block">
          <Sidebar />
        </div>
        <div className="flex min-w-0 flex-1 flex-col">
          <Header />
          <main className="bg-surface-canvas flex-1 overflow-y-auto">
            <div className="mx-auto flex w-full max-w-[1600px] flex-1 flex-col p-4 md:p-6">
              {children}
            </div>
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
