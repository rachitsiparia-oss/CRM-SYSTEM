import { Construction } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col gap-6">
      <PageHeader
        title="Dashboard"
        description="The operational command center — role-scoped KPIs, activity, and alerts."
      />
      <EmptyState
        icon={Construction}
        title="Not implemented yet"
        description="Real widgets are wired up once each contributing module ships its aggregation endpoints — see ROADMAP.md Phase 5 onward."
        className="flex-1"
      />
    </div>
  );
}
