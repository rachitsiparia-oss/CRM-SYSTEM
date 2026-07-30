"use client";

import { useCommunicationAnalytics } from "@/lib/hooks/use-communications";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatCard } from "@/components/stat-card";
import { ErrorState } from "@/components/error-state";
import { MessageSquare, MessagesSquare, TrendingDown, TrendingUp } from "lucide-react";

export function AnalyticsView() {
  const { data: stats, isLoading, isError, refetch } = useCommunicationAnalytics();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Communication analytics"
        description="Delivery health, message volume by channel, and workload across the team."
      />

      {isError ? (
        <ErrorState title="Could not load analytics" onRetry={() => void refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Inbound messages"
              value={stats?.inbound_count ?? 0}
              icon={MessageSquare}
              loading={isLoading}
            />
            <StatCard
              label="Outbound messages"
              value={stats?.outbound_count ?? 0}
              icon={MessagesSquare}
              loading={isLoading}
            />
            <StatCard
              label="Delivery rate"
              value={
                stats?.delivery_rate !== null && stats?.delivery_rate !== undefined
                  ? `${Math.round(stats.delivery_rate * 100)}%`
                  : "—"
              }
              icon={TrendingUp}
              loading={isLoading}
            />
            <StatCard
              label="Failure rate"
              value={
                stats?.failure_rate !== null && stats?.failure_rate !== undefined
                  ? `${Math.round(stats.failure_rate * 100)}%`
                  : "—"
              }
              icon={TrendingDown}
              loading={isLoading}
            />
          </div>

          <SectionCard title="Messages by channel">
            {stats && Object.keys(stats.messages_by_channel).length > 0 ? (
              <ul className="flex flex-col gap-2">
                {Object.entries(stats.messages_by_channel).map(([channel, count]) => (
                  <li key={channel} className="flex items-center justify-between text-sm">
                    <span className="capitalize">{channel.replace(/_/g, " ")}</span>
                    <span className="font-medium">{count}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground text-sm">No messages sent yet.</p>
            )}
          </SectionCard>
        </>
      )}
    </div>
  );
}
