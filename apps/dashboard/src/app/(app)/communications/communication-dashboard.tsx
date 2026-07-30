"use client";

import { useRouter } from "next/navigation";
import { Inbox, MessagesSquare, CheckCircle2, Clock, ListTodo, Bell } from "lucide-react";

import { useCommunicationAnalytics } from "@/lib/hooks/use-communications";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";

function formatSeconds(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  return `${Math.round(seconds / 60)} min`;
}

export function CommunicationDashboard() {
  const router = useRouter();
  const { data: stats, isLoading, isError, refetch } = useCommunicationAnalytics();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Communication dashboard"
        description="Conversations, response times, and delivery health across every channel."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => router.push("/communications/inbox")}>
              <Inbox className="size-4" />
              Open inbox
            </Button>
            <Button variant="outline" onClick={() => router.push("/communications/tasks")}>
              <ListTodo className="size-4" />
              Tasks
            </Button>
            <Button variant="outline" onClick={() => router.push("/communications/notifications")}>
              <Bell className="size-4" />
              Notifications
            </Button>
          </div>
        }
      />

      {isError ? (
        <ErrorState
          title="Could not load communication stats"
          description="Dashboard statistics could not be loaded right now."
          onRetry={() => void refetch()}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Open conversations"
              value={stats?.open_conversations ?? 0}
              icon={MessagesSquare}
              loading={isLoading}
            />
            <StatCard
              label="Unread"
              value={stats?.unread_conversations ?? 0}
              icon={Inbox}
              loading={isLoading}
            />
            <StatCard
              label="Waiting on staff"
              value={stats?.waiting_on_staff ?? 0}
              icon={Clock}
              loading={isLoading}
            />
            <StatCard
              label="Resolved today"
              value={stats?.resolved_today ?? 0}
              icon={CheckCircle2}
              loading={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SectionCard
              title="Average first response"
              description="Time from a customer's first message to staff reply."
            >
              <span className="text-xl font-semibold">
                {formatSeconds(stats?.average_first_response_seconds ?? null)}
              </span>
            </SectionCard>
            <SectionCard title="Average resolution" description="Time from open to resolved.">
              <span className="text-xl font-semibold">
                {formatSeconds(stats?.average_resolution_seconds ?? null)}
              </span>
            </SectionCard>
          </div>

          <SectionCard
            title="Delivery health"
            description="Across outbound messages that reached a terminal state."
          >
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <p className="text-muted-foreground text-xs">Delivery rate</p>
                <p className="text-lg font-semibold">
                  {stats?.delivery_rate !== null && stats?.delivery_rate !== undefined
                    ? `${Math.round(stats.delivery_rate * 100)}%`
                    : "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Failure rate</p>
                <p className="text-lg font-semibold">
                  {stats?.failure_rate !== null && stats?.failure_rate !== undefined
                    ? `${Math.round(stats.failure_rate * 100)}%`
                    : "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Active suppressions</p>
                <p className="text-lg font-semibold">{stats?.suppression_count ?? 0}</p>
              </div>
            </div>
          </SectionCard>
        </>
      )}
    </div>
  );
}
