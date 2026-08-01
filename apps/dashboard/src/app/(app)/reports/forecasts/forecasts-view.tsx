"use client";

import { useState } from "react";
import type { ForecastArea, ForecastDefinition, ForecastMethod } from "@rkpr/contracts";
import { Plus, TrendingUp } from "lucide-react";

import {
  useCreateForecastDefinition,
  useForecastDefinitionList,
  useForecastSnapshotList,
  useRunForecast,
} from "@/lib/hooks/use-forecasts";
import { humanize, formatDate } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { LineChart } from "@/components/charts/line-chart";

const FORECAST_AREAS: ForecastArea[] = [
  "order_volume",
  "net_revenue",
  "reservation_covers",
  "inventory_consumption",
];
const FORECAST_METHODS: ForecastMethod[] = [
  "moving_average",
  "linear_trend",
  "seasonal_naive",
  "exponential_smoothing",
];
const SNAPSHOT_STATUS_TONE: Record<string, "neutral" | "success" | "warning" | "danger"> = {
  ok: "success",
  insufficient_data: "warning",
  failed: "danger",
};

export function ForecastsView() {
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<ForecastDefinition | null>(null);
  const { data: definitions, isLoading } = useForecastDefinitionList();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Forecasts"
        description="Transparent, deterministic statistical forecasts — moving average, linear trend, seasonal naive, and exponential smoothing."
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="size-4" />
            New forecast
          </Button>
        }
      />

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : !definitions || definitions.length === 0 ? (
        <EmptyState
          title="No forecasts defined"
          description="Define a forecast to project a metric forward using a transparent statistical method."
          action={<Button onClick={() => setShowCreate(true)}>New forecast</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {definitions.map((definition) => (
            <button key={definition.id} type="button" onClick={() => setSelected(definition)} className="text-left">
              <SectionCard
                title={definition.name}
                description={`${humanize(definition.forecast_area)} · ${humanize(definition.method)}`}
                className="h-full hover:border-primary/50 cursor-pointer transition-colors"
              >
                <p className="text-muted-foreground text-xs">
                  Horizon: {definition.horizon_periods} periods
                </p>
              </SectionCard>
            </button>
          ))}
        </div>
      )}

      <CreateForecastModal open={showCreate} onOpenChange={setShowCreate} />
      {selected && (
        <ForecastDetailModal definition={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function CreateForecastModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createForecast = useCreateForecastDefinition();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [area, setArea] = useState<ForecastArea>("net_revenue");
  const [method, setMethod] = useState<ForecastMethod>("moving_average");
  const [targetMetricCode, setTargetMetricCode] = useState("");
  const [horizonPeriods, setHorizonPeriods] = useState("14");
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setCode("");
    setName("");
    setArea("net_revenue");
    setMethod("moving_average");
    setTargetMetricCode("");
    setHorizonPeriods("14");
    setError(null);
  };

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New forecast"
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!code.trim() || !name.trim() || !targetMetricCode.trim() || createForecast.isPending}
            onClick={() => {
              setError(null);
              createForecast.mutate(
                {
                  code: code.trim(),
                  name: name.trim(),
                  forecast_area: area,
                  method,
                  target_metric_code: targetMetricCode.trim(),
                  horizon_periods: Number(horizonPeriods),
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create this forecast."),
                },
              );
            }}
          >
            {createForecast.isPending ? "Creating…" : "Create forecast"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="forecast-code">Code</Label>
            <Input id="forecast-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="forecast-name">Name</Label>
            <Input id="forecast-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Forecast area</Label>
            <Select value={area} onValueChange={(v) => setArea(v as ForecastArea)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FORECAST_AREAS.map((a) => (
                  <SelectItem key={a} value={a}>
                    {humanize(a)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Method</Label>
            <Select value={method} onValueChange={(v) => setMethod(v as ForecastMethod)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {FORECAST_METHODS.map((m) => (
                  <SelectItem key={m} value={m}>
                    {humanize(m)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="forecast-metric">Target metric code</Label>
          <Input
            id="forecast-metric"
            value={targetMetricCode}
            onChange={(e) => setTargetMetricCode(e.target.value)}
            placeholder="e.g. sales_net_revenue"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="forecast-horizon">Horizon (periods)</Label>
          <Input
            id="forecast-horizon"
            type="number"
            min={1}
            value={horizonPeriods}
            onChange={(e) => setHorizonPeriods(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}

function ForecastDetailModal({
  definition,
  onClose,
}: {
  definition: ForecastDefinition;
  onClose: () => void;
}) {
  const runForecast = useRunForecast(definition.id);
  const { data: snapshots, isLoading } = useForecastSnapshotList(definition.id, 1, 10);
  const latest = snapshots?.data[0];

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={definition.name}
      description={`${humanize(definition.forecast_area)} · ${humanize(definition.method)} · target metric ${definition.target_metric_code}`}
      size="lg"
      footer={
        <Button onClick={() => runForecast.mutate()} disabled={runForecast.isPending}>
          <TrendingUp className="size-4" />
          {runForecast.isPending ? "Running…" : "Run forecast"}
        </Button>
      }
    >
      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : !latest ? (
        <EmptyState title="No snapshots yet" description="Run this forecast to generate its first snapshot." />
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <StatusBadge
              label={humanize(latest.status)}
              tone={SNAPSHOT_STATUS_TONE[latest.status] ?? "neutral"}
            />
            {latest.backtest_mae !== null && (
              <span className="text-muted-foreground text-xs">MAE: {latest.backtest_mae.toFixed(2)}</span>
            )}
            {latest.backtest_mape !== null && (
              <span className="text-muted-foreground text-xs">
                MAPE: {latest.backtest_mape.toFixed(1)}%
              </span>
            )}
          </div>

          {latest.status === "insufficient_data" ? (
            <EmptyState
              title="Not enough history"
              description="This forecast needs more historical periods before it can produce a projection."
            />
          ) : latest.status === "failed" ? (
            <p className="text-destructive text-sm">{latest.failure_details}</p>
          ) : latest.forecast_values && latest.forecast_values.length > 0 ? (
            <LineChart
              categories={latest.forecast_values.map((v) => formatDate(v.date))}
              series={[
                {
                  name: definition.target_metric_code,
                  data: latest.forecast_values.map((v) => Number(v.value)),
                },
              ]}
              height={240}
            />
          ) : (
            <EmptyState title="No forecast values" />
          )}

          {latest.assumptions && (
            <p className="text-muted-foreground text-xs">{latest.assumptions}</p>
          )}
        </div>
      )}
    </Modal>
  );
}
