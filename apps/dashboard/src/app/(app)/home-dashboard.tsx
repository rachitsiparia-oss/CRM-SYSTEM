"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ReportWindowCode } from "@rkpr/contracts";
import { ClipboardList, IndianRupee, Repeat, ShoppingCart, UsersRound } from "lucide-react";

import { useDashboard, useTimeseries } from "@/lib/hooks/use-reports";
import { useOrderDashboardStats, useOrderList, useTopMenuItems } from "@/lib/hooks/use-orders";
import {
  formatDateTime,
  formatMinorUnits,
  humanize,
  ORDER_STATUS_TONES,
} from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { MetricCard } from "@/components/metric-card";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { BarChart } from "@/components/charts/bar-chart";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { WindowSelect, type CustomRange } from "./reports/window-select";

const KPI_DEFS = [
  { code: "exec_net_sales", domain: "executive", label: "Total revenue", icon: IndianRupee },
  { code: "exec_completed_orders", domain: "executive", label: "Completed orders", icon: ShoppingCart },
  { code: "customers_total", domain: "customers", label: "Active customers", icon: UsersRound },
  { code: "customers_repeat_rate", domain: "customers", label: "Repeat customer rate", icon: Repeat },
] as const;

/** Currency metrics carry raw integer minor units (paise) end to end, per
 * CLAUDE.md section 7 — only display formatting happens here. */
function formatKpiValue(value: number, unit: string | null): string {
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "INR_minor") return formatMinorUnits(value);
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
}

function formatChartDay(isoDate: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    timeZone: "Asia/Kolkata",
  }).format(new Date(isoDate));
}

export function HomeDashboard() {
  const router = useRouter();
  const [windowCode, setWindowCode] = useState<ReportWindowCode>("current_week");
  const [customRange, setCustomRange] = useState<CustomRange>({ start: "", end: "" });
  const customRangeReady = customRange.start && customRange.end ? customRange : undefined;
  const effectiveRange = windowCode === "custom" ? customRangeReady : undefined;

  const executive = useDashboard("executive", windowCode, effectiveRange);
  const customers = useDashboard("customers", windowCode, effectiveRange);
  const timeseries = useTimeseries("exec_net_sales", 7);
  const topItems = useTopMenuItems(windowCode);
  const activity = useOrderDashboardStats();
  const recentOrders = useOrderList({ page: 1, pageSize: 5, sort: "newest" });

  const dashboardsByDomain = { executive: executive.data, customers: customers.data };
  const kpisLoading = executive.isLoading || customers.isLoading;
  const kpisReady = windowCode !== "custom" || !!customRangeReady;

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Dashboard"
        description="The operational command center — role-scoped KPIs, activity, and alerts."
        actions={
          <div className="flex flex-wrap items-end gap-2">
            <WindowSelect
              value={windowCode}
              onChange={setWindowCode}
              customRange={customRange}
              onCustomRangeChange={setCustomRange}
            />
            <Button variant="outline" onClick={() => router.push("/orders/list")}>
              View all orders
            </Button>
          </div>
        }
      />

      {!kpisReady ? (
        <EmptyState
          title="Choose a custom date range"
          description="Pick both a start and end date to load this dashboard."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {kpisLoading
            ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)
            : KPI_DEFS.map((def) => {
                const metric = dashboardsByDomain[def.domain]?.metrics.find(
                  (m) => m.metric_code === def.code,
                );
                if (!metric) return null;
                return (
                  <MetricCard
                    key={def.code}
                    label={def.label}
                    value={formatKpiValue(metric.value, metric.unit)}
                    changePercent={
                      metric.change_pct !== null ? Math.round(metric.change_pct * 10) / 10 : undefined
                    }
                    icon={def.icon}
                  />
                );
              })}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <SectionCard
          title="Weekly sales trend"
          description="Net sales for the last 7 days."
          className="lg:col-span-2"
        >
          {timeseries.isError ? (
            <ErrorState
              title="Could not load the sales trend"
              onRetry={() => void timeseries.refetch()}
            />
          ) : !timeseries.isLoading && (!timeseries.data || timeseries.data.points.every((p) => p.value === 0)) ? (
            <EmptyState
              title="No sales yet"
              description="This chart fills in once completed orders start coming in."
            />
          ) : (
            <BarChart
              loading={timeseries.isLoading}
              categories={timeseries.data?.points.map((p) => formatChartDay(p.date)) ?? []}
              series={[
                { name: "Net sales", data: timeseries.data?.points.map((p) => p.value / 100) ?? [] },
              ]}
              highlightIndex={(timeseries.data?.points.length ?? 1) - 1}
              height={260}
            />
          )}
        </SectionCard>

        <SectionCard title="Top menu items" description="Best sellers by revenue this window.">
          {topItems.isError ? (
            <ErrorState title="Could not load top items" onRetry={() => void topItems.refetch()} />
          ) : topItems.isLoading ? (
            <div className="flex flex-col gap-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !topItems.data || topItems.data.length === 0 ? (
            <EmptyState
              title="No sales yet"
              description="Best-selling items will appear here once orders are completed."
            />
          ) : (
            <ul className="flex flex-col gap-4">
              {(() => {
                const maxRevenue = Math.max(...topItems.data.map((i) => i.revenue_minor), 1);
                return topItems.data.map((item) => (
                  <li key={item.product_name} className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="truncate font-medium">{item.product_name}</span>
                      <span className="text-muted-foreground shrink-0 text-xs">
                        {item.quantity_sold} sold · {formatMinorUnits(item.revenue_minor)}
                      </span>
                    </div>
                    <Progress
                      value={(item.revenue_minor / maxRevenue) * 100}
                      indicatorClassName="bg-brand-yellow"
                    />
                  </li>
                ));
              })()}
            </ul>
          )}
        </SectionCard>
      </div>

      <SectionCard
        title="Recent orders"
        description="The five most recent orders across every source."
        actions={
          <Button variant="outline" size="sm" onClick={() => router.push("/orders/list")}>
            View all
          </Button>
        }
      >
        {recentOrders.isError ? (
          <ErrorState title="Could not load recent orders" onRetry={() => void recentOrders.refetch()} />
        ) : recentOrders.isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : !recentOrders.data || recentOrders.data.data.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No orders yet"
            description="New orders will show up here as soon as they come in."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Order</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentOrders.data.data.map((order) => (
                <TableRow key={order.id}>
                  <TableCell>
                    <Link href={`/orders/${order.id}`} className="font-medium hover:underline">
                      {order.order_number}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <StatusBadge label={humanize(order.status)} tone={ORDER_STATUS_TONES[order.status]} />
                  </TableCell>
                  <TableCell className="text-sm">{humanize(order.source)}</TableCell>
                  <TableCell className="text-sm font-medium">
                    {formatMinorUnits(order.grand_total_minor)}
                  </TableCell>
                  <TableCell className="text-sm">{formatDateTime(order.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </SectionCard>

      <SectionCard title="Recent activity" description="The latest events across all orders.">
        {activity.isError ? (
          <ErrorState title="Could not load recent activity" onRetry={() => void activity.refetch()} />
        ) : activity.isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : !activity.data || activity.data.recent_activity.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No recent activity"
            description="Order events will appear here as soon as something happens."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {activity.data.recent_activity.map((entry, index) => (
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
    </div>
  );
}
