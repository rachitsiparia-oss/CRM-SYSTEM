"use client";

import { useState } from "react";
import type {
  ExportFormat,
  ReportDefinition,
  ReportingArea,
  ReportRun,
  ReportWindowCode,
} from "@rkpr/contracts";
import { Download, Play, Plus } from "lucide-react";

import {
  useCreateReportDefinition,
  useMetricCatalog,
  useReportDefinitionList,
  useReportRunList,
  useRunReportDefinition,
} from "@/lib/hooks/use-reports";
import { useCreateExport, useExportDetail, useExportDownloadUrl } from "@/lib/hooks/use-report-exports";
import { humanize, formatDateTime } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { DataTablePagination } from "@/components/data-table/data-table-pagination";
import { WINDOW_OPTIONS } from "../window-select";

const REPORTING_AREAS: ReportingArea[] = [
  "executive",
  "sales",
  "orders",
  "customers",
  "leads",
  "reservations",
  "menu_products",
  "inventory_suppliers",
  "marketing",
  "loyalty",
  "feedback",
  "complaints",
  "communication",
  "staff_tasks",
  "system_operations",
];

const RUN_STATUS_TONE: Record<string, "neutral" | "info" | "success" | "warning" | "danger"> = {
  pending: "neutral",
  running: "info",
  completed: "success",
  failed: "danger",
};

export function ReportLibraryView() {
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedDefinitionId, setSelectedDefinitionId] = useState<string | null>(null);

  const { data: definitions, isLoading } = useReportDefinitionList({ page, pageSize: 20 });

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Report Library"
        description="Saved report definitions, on-demand runs, and exports."
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="size-4" />
            New report
          </Button>
        }
      />

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : !definitions || definitions.data.length === 0 ? (
        <EmptyState
          title="No report definitions yet"
          description="Create a report to save a metric selection you'll want to run again."
          action={<Button onClick={() => setShowCreate(true)}>New report</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {definitions.data.map((definition) => (
            <button
              key={definition.id}
              type="button"
              onClick={() => setSelectedDefinitionId(definition.id)}
              className="text-left"
            >
              <SectionCard
                title={definition.name}
                description={`${humanize(definition.domain)} — ${definition.metric_codes.length} metric${definition.metric_codes.length === 1 ? "" : "s"}`}
                className="h-full hover:border-primary/50 cursor-pointer transition-colors"
                actions={
                  <StatusBadge
                    label={definition.definition_type === "system" ? "System" : "Custom"}
                    tone={definition.definition_type === "system" ? "info" : "neutral"}
                  />
                }
              >
                <p className="text-muted-foreground text-xs">
                  {definition.description || "No description."}
                </p>
              </SectionCard>
            </button>
          ))}
        </div>
      )}

      <CreateReportModal open={showCreate} onOpenChange={setShowCreate} />

      {definitions && definitions.pagination.total > definitions.pagination.page_size && (
        <DataTablePagination
          pageIndex={page - 1}
          pageCount={Math.ceil(definitions.pagination.total / definitions.pagination.page_size)}
          total={definitions.pagination.total}
          pageSize={definitions.pagination.page_size}
          onPageChange={(pageIndex) => setPage(pageIndex + 1)}
        />
      )}

      {selectedDefinitionId && (
        <ReportDefinitionDetail
          definition={definitions?.data.find((d) => d.id === selectedDefinitionId) ?? null}
          onClose={() => setSelectedDefinitionId(null)}
        />
      )}
    </div>
  );
}

function CreateReportModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [domain, setDomain] = useState<ReportingArea>("sales");
  const [defaultWindow, setDefaultWindow] = useState<ReportWindowCode>("current_month");
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const { data: metrics, isLoading: metricsLoading } = useMetricCatalog();
  const createDefinition = useCreateReportDefinition();

  const domainMetrics = metrics?.filter((m) => m.domain === domain) ?? [];

  const reset = () => {
    setName("");
    setDescription("");
    setDomain("sales");
    setDefaultWindow("current_month");
    setSelectedMetrics([]);
    setError(null);
  };

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New report"
      description="Save a metric selection you can re-run, export, or schedule."
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!name.trim() || selectedMetrics.length === 0 || createDefinition.isPending}
            onClick={() => {
              setError(null);
              createDefinition.mutate(
                {
                  name: name.trim(),
                  description: description.trim() || null,
                  domain,
                  metric_codes: selectedMetrics,
                  default_window: defaultWindow,
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create this report."),
                },
              );
            }}
          >
            {createDefinition.isPending ? "Creating…" : "Create report"}
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
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="report-name">Name</Label>
          <Input id="report-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="report-description">Description (optional)</Label>
          <Textarea
            id="report-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Domain</Label>
            <Select
              value={domain}
              onValueChange={(v) => {
                setDomain(v as ReportingArea);
                setSelectedMetrics([]);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {REPORTING_AREAS.map((area) => (
                  <SelectItem key={area} value={area}>
                    {humanize(area)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Default window</Label>
            <Select value={defaultWindow} onValueChange={(v) => setDefaultWindow(v as ReportWindowCode)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {WINDOW_OPTIONS.filter((o) => o.value !== "custom").map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Metrics</Label>
          {metricsLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : domainMetrics.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No metrics visible in this domain for your role.
            </p>
          ) : (
            <div className="flex max-h-56 flex-col gap-2 overflow-y-auto rounded-md border p-3">
              {domainMetrics.map((metric) => (
                <label key={metric.code} className="flex items-start gap-2 text-sm">
                  <Checkbox
                    checked={selectedMetrics.includes(metric.code)}
                    onCheckedChange={(checked) =>
                      setSelectedMetrics((prev) =>
                        checked ? [...prev, metric.code] : prev.filter((c) => c !== metric.code),
                      )
                    }
                  />
                  <span>
                    <span className="font-medium">{metric.display_name}</span>
                    <span className="text-muted-foreground block text-xs">{metric.description}</span>
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

function ReportDefinitionDetail({
  definition,
  onClose,
}: {
  definition: ReportDefinition | null;
  onClose: () => void;
}) {
  const [exportRun, setExportRun] = useState<ReportRun | null>(null);
  const { data: runs, isLoading } = useReportRunList({
    page: 1,
    pageSize: 10,
    reportDefinitionId: definition?.id,
  });
  const runReport = useRunReportDefinition(definition?.id ?? "");

  return (
    <Modal
      open={!!definition}
      onOpenChange={(open) => !open && onClose()}
      title={definition?.name ?? ""}
      description={definition?.description ?? undefined}
      size="lg"
      footer={
        <Button
          onClick={() => definition && runReport.mutate({ window_code: definition.default_window })}
          disabled={runReport.isPending}
        >
          <Play className="size-4" />
          {runReport.isPending ? "Running…" : "Run now"}
        </Button>
      }
    >
      <div className="flex flex-col gap-3">
        <h3 className="text-sm font-medium">Recent runs</h3>
        {isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : !runs || runs.data.length === 0 ? (
          <EmptyState title="No runs yet" description="Run this report to generate its first snapshot." />
        ) : (
          <div className="flex flex-col gap-2">
            {runs.data.map((run) => (
              <div key={run.id} className="flex items-center justify-between gap-2 rounded-md border p-2.5 text-sm">
                <div className="flex flex-col">
                  <span>
                    {humanize(run.window_code)} — {formatDateTime(run.completed_at ?? run.started_at)}
                  </span>
                  <span className="text-muted-foreground text-xs">{humanize(run.trigger_source)} run</span>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge label={humanize(run.status)} tone={RUN_STATUS_TONE[run.status] ?? "neutral"} />
                  {run.status === "completed" && (
                    <Button size="sm" variant="ghost" onClick={() => setExportRun(run)}>
                      <Download className="size-3.5" />
                      Export
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <ExportModal run={exportRun} onOpenChange={(open) => !open && setExportRun(null)} />
    </Modal>
  );
}

function ExportModal({
  run,
  onOpenChange,
}: {
  run: ReportRun | null;
  onOpenChange: (open: boolean) => void;
}) {
  const [format, setFormat] = useState<ExportFormat>("csv");
  const [artifactId, setArtifactId] = useState<string | null>(null);
  const createExport = useCreateExport();
  const { data: artifact } = useExportDetail(artifactId ?? undefined);
  const getDownloadUrl = useExportDownloadUrl();

  return (
    <Modal
      open={!!run}
      onOpenChange={(open) => {
        if (!open) {
          setArtifactId(null);
        }
        onOpenChange(open);
      }}
      title="Export report run"
      size="sm"
      footer={
        artifact?.status === "completed" ? (
          <Button
            onClick={() =>
              getDownloadUrl.mutate(artifact.id, {
                onSuccess: (response) => window.open(response.data.download_url, "_blank"),
              })
            }
          >
            <Download className="size-4" />
            Download
          </Button>
        ) : (
          <Button
            disabled={!run || createExport.isPending || !!artifactId}
            onClick={() =>
              run &&
              createExport.mutate(
                { report_run_id: run.id, export_format: format },
                { onSuccess: (response) => setArtifactId(response.data.id) },
              )
            }
          >
            {createExport.isPending ? "Starting…" : "Generate export"}
          </Button>
        )
      }
    >
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Label>Format</Label>
          <Select value={format} onValueChange={(v) => setFormat(v as ExportFormat)} disabled={!!artifactId}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="xlsx">Excel (XLSX)</SelectItem>
              <SelectItem value="pdf">PDF</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {artifact && (
          <p className="text-muted-foreground text-sm">
            Status: <StatusBadge label={humanize(artifact.status)} tone={artifact.status === "failed" ? "danger" : "info"} />
          </p>
        )}
        {artifact?.status === "failed" && (
          <p className="text-destructive text-sm">{artifact.failure_details}</p>
        )}
      </div>
    </Modal>
  );
}
