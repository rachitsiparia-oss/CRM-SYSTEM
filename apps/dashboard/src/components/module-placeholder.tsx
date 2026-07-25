import { Construction } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";

/** Shell page for a module whose real implementation hasn't shipped yet —
 * PROJECT_PLAN.md Phase 4 scope: "Create shell pages only. No business
 * logic." Title, breadcrumb (rendered by the layout's Header), and a
 * placeholder. Nothing more — real widgets, tables, and forms land when
 * each module's own phase is implemented. */
export function ModulePlaceholder({ title }: { title: string }) {
  return (
    <div className="flex flex-1 flex-col gap-6">
      <PageHeader title={title} />
      <EmptyState
        icon={Construction}
        title="Not implemented yet"
        description="This module is scheduled in a later phase — see ROADMAP.md for its delivery order."
        className="flex-1"
      />
    </div>
  );
}
