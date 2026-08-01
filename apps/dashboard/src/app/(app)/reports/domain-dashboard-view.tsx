"use client";

import { useState } from "react";
import type { ReportWindowCode } from "@rkpr/contracts";
import { AlertTriangle } from "lucide-react";

import { useDashboard, useDrilldown } from "@/lib/hooks/use-reports";
import { humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { MetricCard } from "@/components/metric-card";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Modal } from "@/components/modals/modal";
import { Skeleton } from "@/components/ui/skeleton";
import { WindowSelect, type CustomRange } from "./window-select";

// A deliberately small, hand-written allowlist matching
// app/reports/service.py's `get_drilldown()` — this phase's documented
// scoping decision rather than a generic per-metric drill-down mechanism.
const DRILLDOWN_METRIC_CODES = new Set([
  "exec_open_high_severity_complaints",
  "leads_open",
  "inventory_low_stock_items",
  "inventory_critical_stock_items",
  "sales_cancelled_order_count",
  "staff_overdue_tasks",
  "reservations_no_show_rate",
]);

export interface DomainDashboardViewProps {
  domain: string;
  title: string;
  description: string;
}

export function DomainDashboardView({ domain, title, description }: DomainDashboardViewProps) {
  const [windowCode, setWindowCode] = useState<ReportWindowCode>("current_month");
  const [customRange, setCustomRange] = useState<CustomRange>({ start: "", end: "" });
  const [drilldownMetric, setDrilldownMetric] = useState<string | null>(null);

  const customRangeReady = customRange.start && customRange.end ? customRange : undefined;
  const { data, isLoading, isError, refetch } = useDashboard(
    domain,
    windowCode,
    windowCode === "custom" ? customRangeReady : undefined,
  );

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title={title} description={description} />

      <WindowSelect
        value={windowCode}
        onChange={setWindowCode}
        customRange={customRange}
        onCustomRangeChange={setCustomRange}
      />

      {isError ? (
        <ErrorState title="Could not load this dashboard" onRetry={() => void refetch()} />
      ) : windowCode === "custom" && !customRangeReady ? (
        <EmptyState title="Choose a custom date range" description="Pick both a start and end date to load this dashboard." />
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      ) : !data || data.metrics.length === 0 ? (
        <EmptyState
          title="No metrics available"
          description="Your role doesn't have visibility into any metric in this domain, or none are defined yet."
        />
      ) : (
        <>
          {data.partial_failures.length > 0 && (
            <Alert>
              <AlertTriangle className="size-4" />
              <AlertTitle>Some metrics couldn&apos;t be loaded</AlertTitle>
              <AlertDescription>
                {data.partial_failures.length} metric{data.partial_failures.length === 1 ? "" : "s"}{" "}
                were skipped — you may not have permission to view them, or they hit an error. The
                rest of this dashboard is still accurate.
              </AlertDescription>
            </Alert>
          )}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {data.metrics.map((metric) => {
              const clickable = DRILLDOWN_METRIC_CODES.has(metric.metric_code);
              return (
                <button
                  key={metric.metric_code}
                  type="button"
                  disabled={!clickable}
                  onClick={() => clickable && setDrilldownMetric(metric.metric_code)}
                  className={clickable ? "text-left" : "cursor-default text-left"}
                >
                  <MetricCard
                    label={metric.display_name}
                    value={formatMetricValue(metric.value, metric.unit)}
                    changePercent={
                      metric.change_pct !== null ? Math.round(metric.change_pct * 10) / 10 : undefined
                    }
                    className={clickable ? "hover:border-primary/50 transition-colors" : undefined}
                  />
                </button>
              );
            })}
          </div>
        </>
      )}

      <DrilldownModal
        metricCode={drilldownMetric}
        windowCode={windowCode}
        onOpenChange={(open) => !open && setDrilldownMetric(null)}
      />
    </div>
  );
}

function formatMetricValue(value: number, unit: string | null): string {
  if (unit === "percent") return `${value.toFixed(1)}%`;
  if (unit === "minor_unit") return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
}

function DrilldownModal({
  metricCode,
  windowCode,
  onOpenChange,
}: {
  metricCode: string | null;
  windowCode: string;
  onOpenChange: (open: boolean) => void;
}) {
  const { data, isLoading } = useDrilldown(metricCode ?? undefined, windowCode);

  return (
    <Modal
      open={!!metricCode}
      onOpenChange={onOpenChange}
      title={metricCode ? humanize(metricCode) : ""}
      description="Underlying records behind this metric, most recent first."
      size="lg"
    >
      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : !data || data.records.length === 0 ? (
        <EmptyState title="No records" />
      ) : (
        <div className="flex flex-col gap-2">
          {data.records.map((record) => (
            <div
              key={`${record.record_type}-${record.record_id}`}
              className="flex flex-col gap-1 rounded-md border p-3 text-sm"
            >
              <span className="font-medium">{record.label}</span>
              <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-0.5 text-xs">
                {Object.entries(record.detail).map(([key, value]) => (
                  <span key={key}>
                    {humanize(key)}: {String(value)}
                  </span>
                ))}
              </div>
            </div>
          ))}
          {data.truncated && (
            <p className="text-muted-foreground text-xs">
              Showing the first {data.records.length} records only.
            </p>
          )}
        </div>
      )}
    </Modal>
  );
}
