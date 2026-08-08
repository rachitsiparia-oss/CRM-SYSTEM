"use client";

import { useState } from "react";
import Link from "next/link";
import type { ReportWindowCode } from "@rkpr/contracts";
import {
  AlertTriangle,
  BarChart3,
  Bot,
  CalendarClock,
  ClipboardList,
  Gift,
  ShoppingCart,
  TrendingUp,
  UserPlus,
  UsersRound,
  Utensils,
  Warehouse,
} from "lucide-react";

import { useDashboard } from "@/lib/hooks/use-reports";
import { PageHeader } from "@/components/page-header";
import { MetricCard } from "@/components/metric-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { WindowSelect, type CustomRange } from "./window-select";

const SECTIONS = [
  { href: "/reports/sales", icon: ShoppingCart, title: "Sales", description: "Revenue, orders, and average ticket size." },
  { href: "/reports/customers", icon: UsersRound, title: "Customers", description: "Growth, retention, and lifetime value." },
  { href: "/reports/leads", icon: UserPlus, title: "Leads", description: "Pipeline volume and conversion." },
  { href: "/reports/reservations", icon: CalendarClock, title: "Reservations", description: "Covers, no-shows, and table utilization." },
  { href: "/reports/inventory", icon: Warehouse, title: "Inventory & Suppliers", description: "Stock health and supplier performance." },
  { href: "/reports/marketing", icon: TrendingUp, title: "Marketing", description: "Campaign and offer performance." },
  { href: "/reports/loyalty", icon: Gift, title: "Loyalty", description: "Membership, tiers, and redemption." },
  { href: "/reports/feedback", icon: BarChart3, title: "Feedback", description: "Ratings and review-request performance." },
  { href: "/reports/complaints", icon: AlertTriangle, title: "Complaints", description: "Case volume, SLA, and severity." },
  { href: "/reports/staff", icon: Utensils, title: "Staff & Tasks", description: "Task completion and staffing metrics." },
  { href: "/reports/library", icon: ClipboardList, title: "Report Library", description: "Saved report definitions, runs, and exports." },
  { href: "/reports/schedules", icon: CalendarClock, title: "Scheduled Reports", description: "Recurring report delivery and history." },
  { href: "/reports/anomalies", icon: AlertTriangle, title: "Anomaly Center", description: "Deterministic anomaly rules and findings." },
  { href: "/reports/forecasts", icon: TrendingUp, title: "Forecasts", description: "Transparent statistical forecasts." },
  { href: "/reports/ai", icon: Bot, title: "AI Center", description: "Controlled, advisory AI requests and history." },
];

export function ReportsDashboard() {
  const [windowCode, setWindowCode] = useState<ReportWindowCode>("current_month");
  const [customRange, setCustomRange] = useState<CustomRange>({ start: "", end: "" });
  const customRangeReady = customRange.start && customRange.end ? customRange : undefined;
  const { data, isLoading, isError, refetch } = useDashboard(
    "executive",
    windowCode,
    windowCode === "custom" ? customRangeReady : undefined,
  );

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Reports, Analytics & AI Center"
        description="Executive overview across the business, plus domain dashboards, the report library, scheduled reports, anomaly detection, forecasts, and controlled AI."
      />

      <WindowSelect
        value={windowCode}
        onChange={setWindowCode}
        customRange={customRange}
        onCustomRangeChange={setCustomRange}
      />

      {isError ? (
        <ErrorState title="Could not load the executive dashboard" onRetry={() => void refetch()} />
      ) : windowCode === "custom" && !customRangeReady ? (
        <EmptyState title="Choose a custom date range" description="Pick both a start and end date to load this dashboard." />
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : !data || data.metrics.length === 0 ? (
        <EmptyState title="No executive metrics available" />
      ) : (
        <>
          {data.partial_failures.length > 0 && (
            <Alert>
              <AlertTriangle className="size-4" />
              <AlertTitle>Some metrics couldn&apos;t be loaded</AlertTitle>
              <AlertDescription>
                {data.partial_failures.length} metric{data.partial_failures.length === 1 ? "" : "s"}{" "}
                were skipped for this account.
              </AlertDescription>
            </Alert>
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {data.metrics.map((metric) => (
              <MetricCard
                key={metric.metric_code}
                label={metric.display_name}
                value={
                  metric.unit === "%"
                    ? `${metric.value.toFixed(1)}%`
                    : Number.isInteger(metric.value)
                      ? metric.value.toLocaleString()
                      : metric.value.toFixed(2)
                }
                changePercent={
                  metric.change_pct !== null ? Math.round(metric.change_pct * 10) / 10 : undefined
                }
              />
            ))}
          </div>
        </>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SECTIONS.map((section) => (
          <Link key={section.href} href={section.href}>
            <Card className="h-full transition-colors hover:border-primary/50">
              <CardHeader className="flex flex-row items-center gap-3">
                <section.icon className="text-muted-foreground size-5" />
                <div>
                  <CardTitle className="text-base">{section.title}</CardTitle>
                  <CardDescription>{section.description}</CardDescription>
                </div>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
