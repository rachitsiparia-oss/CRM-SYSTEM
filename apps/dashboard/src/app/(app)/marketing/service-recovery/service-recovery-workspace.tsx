"use client";

import { useRecoveryAnalytics } from "@/lib/hooks/use-service-recovery";
import { formatMinorUnits } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RecoveryActionList } from "./recovery-action-list";
import { ApprovalRuleList } from "./approval-rule-list";

export function ServiceRecoveryWorkspace() {
  const { data: analytics, isLoading } = useRecoveryAnalytics();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Service Recovery"
        description="Compensation proposed for complaints, approval routing, and execution through the loyalty, credit, and order modules."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Compensation value (30d)"
          value={formatMinorUnits(analytics?.total_value_minor_30d)}
          loading={isLoading}
        />
        <StatCard
          label="Loyalty points issued (30d)"
          value={analytics?.total_points_30d ?? 0}
          loading={isLoading}
        />
        <StatCard
          label="Approved (30d)"
          value={analytics?.approved_count_30d ?? 0}
          loading={isLoading}
        />
        <StatCard
          label="Completion rate"
          value={analytics ? `${analytics.completion_rate_pct.toFixed(0)}%` : "—"}
          loading={isLoading}
        />
      </div>

      <Tabs defaultValue="actions">
        <TabsList>
          <TabsTrigger value="actions">Recovery Actions</TabsTrigger>
          <TabsTrigger value="approval-rules">Approval Rules</TabsTrigger>
        </TabsList>

        <TabsContent value="actions" className="mt-4">
          <RecoveryActionList />
        </TabsContent>

        <TabsContent value="approval-rules" className="mt-4">
          <ApprovalRuleList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
