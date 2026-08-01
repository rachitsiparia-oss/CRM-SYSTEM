"use client";

import { useComplaintAnalytics } from "@/lib/hooks/use-complaints";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ComplaintList } from "./complaint-list";
import { SlaPolicyList } from "./sla-policy-list";

export function ComplaintsWorkspace() {
  const { data: analytics, isLoading } = useComplaintAnalytics();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Complaints"
        description="Complaint case management, SLA tracking, and escalation."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Open complaints" value={analytics?.open_count ?? 0} loading={isLoading} />
        <StatCard label="New (30d)" value={analytics?.new_30d ?? 0} loading={isLoading} />
        <StatCard
          label="SLA breach rate"
          value={analytics ? `${analytics.sla_breach_rate_pct.toFixed(1)}%` : "—"}
          loading={isLoading}
        />
        <StatCard
          label="Escalation rate"
          value={analytics ? `${analytics.escalation_rate_pct.toFixed(1)}%` : "—"}
          loading={isLoading}
        />
      </div>

      <Tabs defaultValue="complaints">
        <TabsList>
          <TabsTrigger value="complaints">Complaints</TabsTrigger>
          <TabsTrigger value="sla-policies">SLA Policies</TabsTrigger>
        </TabsList>

        <TabsContent value="complaints" className="mt-4">
          <ComplaintList />
        </TabsContent>

        <TabsContent value="sla-policies" className="mt-4">
          <SlaPolicyList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
