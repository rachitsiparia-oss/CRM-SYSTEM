"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ClipboardList,
  CookingPot,
  BellRing,
  CheckCircle2,
  XCircle,
  IndianRupee,
  Receipt,
  Plus,
} from "lucide-react";

import { useOrderDashboardStats } from "@/lib/hooks/use-orders";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, formatMinorUnits, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";

export function OrdersDashboard() {
  const router = useRouter();
  const { data: currentUser } = useCurrentUser();
  const { data: stats, isLoading, isError, refetch } = useOrderDashboardStats();
  const canCreate = hasPermission(currentUser, "orders.create");

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Orders dashboard"
        description="Today's order activity across every source and status."
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => router.push("/orders/list")}>
              View all orders
            </Button>
            {canCreate && (
              <Button onClick={() => router.push("/orders/new")}>
                <Plus className="size-4" />
                New order
              </Button>
            )}
          </div>
        }
      />

      {isError ? (
        <ErrorState
          title="Could not load dashboard stats"
          description="Order statistics could not be loaded right now."
          onRetry={() => void refetch()}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Today's orders" value={stats?.today_order_count ?? 0} icon={ClipboardList} loading={isLoading} />
            <StatCard
              label="Revenue today"
              value={formatMinorUnits(stats?.revenue_today_minor ?? 0)}
              icon={IndianRupee}
              loading={isLoading}
            />
            <StatCard
              label="Average order value"
              value={formatMinorUnits(stats?.average_order_value_minor ?? 0)}
              icon={Receipt}
              loading={isLoading}
            />
            <StatCard
              label="Completed today"
              value={stats?.status_counts_today.completed ?? 0}
              icon={CheckCircle2}
              loading={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Pending confirmation"
              value={stats?.status_counts_today.pending_confirmation ?? 0}
              icon={BellRing}
              loading={isLoading}
            />
            <StatCard
              label="Preparing"
              value={stats?.status_counts_today.preparing ?? 0}
              icon={CookingPot}
              loading={isLoading}
            />
            <StatCard
              label="Ready"
              value={stats?.status_counts_today.ready ?? 0}
              icon={ClipboardList}
              loading={isLoading}
            />
            <StatCard
              label="Cancelled today"
              value={stats?.status_counts_today.cancelled ?? 0}
              icon={XCircle}
              loading={isLoading}
            />
          </div>

          <SectionCard title="Recent activity" description="The latest events across all orders.">
            {!stats || stats.recent_activity.length === 0 ? (
              <EmptyState
                icon={ClipboardList}
                title="No recent activity"
                description="Order events will appear here as soon as something happens."
              />
            ) : (
              <ul className="flex flex-col gap-3">
                {stats.recent_activity.map((entry, index) => (
                  <li key={`${entry.order_id}-${index}`} className="flex items-start justify-between gap-3 text-sm">
                    <div>
                      <Link href={`/orders/${entry.order_id}`} className="font-medium hover:underline">
                        {entry.order_number}
                      </Link>
                      <span className="text-muted-foreground"> · {humanize(entry.event_type)}</span>
                      <p className="text-muted-foreground">{entry.summary}</p>
                    </div>
                    <span className="text-muted-foreground shrink-0 text-xs">
                      {formatDateTime(entry.occurred_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>
        </>
      )}
    </div>
  );
}
