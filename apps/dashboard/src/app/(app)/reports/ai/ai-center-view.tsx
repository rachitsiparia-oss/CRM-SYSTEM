"use client";

import { useState } from "react";
import type { AiFeatureCode, AiRequestFeedbackInput } from "@rkpr/contracts";
import { Bot, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";

import { useCreateAiRequest, useAiRequestDetail, useSubmitAiFeedback } from "@/lib/hooks/use-controlled-ai";
import { useAnomalyFindingList } from "@/lib/hooks/use-anomalies";
import { useDashboard, useMetricCatalog, useReportRunList } from "@/lib/hooks/use-reports";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const FEATURES: { code: AiFeatureCode; label: string; description: string }[] = [
  {
    code: "dashboard_summary",
    label: "Dashboard summary",
    description: "Plain-language summary of a domain dashboard's current metrics.",
  },
  {
    code: "metric_change_explanation",
    label: "Metric change explanation",
    description: "Explain why a single metric changed vs. its comparison period.",
  },
  {
    code: "anomaly_evidence_summary",
    label: "Anomaly evidence summary",
    description: "Summarize a detected anomaly's evidence for staff review.",
  },
  {
    code: "report_narrative",
    label: "Report narrative",
    description: "Draft a short narrative for a completed report run.",
  },
  {
    code: "nl_question_query_plan",
    label: "Ask a question",
    description: "Translate a natural-language analytics question into a metric + window plan.",
  },
];

const STATUS_TONE: Record<string, "neutral" | "info" | "success" | "warning" | "danger"> = {
  pending: "info",
  completed: "success",
  failed: "danger",
  blocked: "warning",
};

export function AiCenterView() {
  const [activeFeature, setActiveFeature] = useState<AiFeatureCode>("nl_question_query_plan");
  const [requestId, setRequestId] = useState<string | null>(null);

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="AI Center"
        description="Controlled, advisory AI — grounded in real CRM data, never an autonomous action. Every request and response is audited."
      />

      <Tabs
        value={activeFeature}
        onValueChange={(v) => {
          setActiveFeature(v as AiFeatureCode);
          setRequestId(null);
        }}
      >
        <TabsList className="flex-wrap">
          {FEATURES.map((f) => (
            <TabsTrigger key={f.code} value={f.code}>
              {f.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {FEATURES.map((f) => (
          <TabsContent key={f.code} value={f.code} className="flex flex-col gap-4">
            <p className="text-muted-foreground text-sm">{f.description}</p>
            <FeatureForm feature={f.code} onRequested={setRequestId} />
          </TabsContent>
        ))}
      </Tabs>

      {requestId && <AiResultCard requestId={requestId} />}
    </div>
  );
}

function FeatureForm({
  feature,
  onRequested,
}: {
  feature: AiFeatureCode;
  onRequested: (id: string) => void;
}) {
  const createRequest = useCreateAiRequest();
  const [error, setError] = useState<string | null>(null);

  const submit = (params: Record<string, unknown>) => {
    setError(null);
    createRequest.mutate(
      { feature_code: feature, params },
      {
        onSuccess: (response) => onRequested(response.data.id),
        onError: (err) => setError(err instanceof ApiError ? err.message : "Could not submit this request."),
      },
    );
  };

  return (
    <SectionCard title="Request">
      <div className="flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
        {feature === "dashboard_summary" && (
          <DashboardSummaryForm onSubmit={submit} pending={createRequest.isPending} />
        )}
        {feature === "metric_change_explanation" && (
          <MetricChangeForm onSubmit={submit} pending={createRequest.isPending} />
        )}
        {feature === "anomaly_evidence_summary" && (
          <AnomalyEvidenceForm onSubmit={submit} pending={createRequest.isPending} />
        )}
        {feature === "report_narrative" && (
          <ReportNarrativeForm onSubmit={submit} pending={createRequest.isPending} />
        )}
        {feature === "nl_question_query_plan" && (
          <QuestionForm onSubmit={submit} pending={createRequest.isPending} />
        )}
      </div>
    </SectionCard>
  );
}

const DASHBOARD_DOMAINS = [
  "executive",
  "sales",
  "customers",
  "leads",
  "reservations",
  "inventory_suppliers",
  "marketing",
  "loyalty",
  "feedback",
  "complaints",
  "staff_tasks",
];

function DashboardSummaryForm({
  onSubmit,
  pending,
}: {
  onSubmit: (params: Record<string, unknown>) => void;
  pending: boolean;
}) {
  const [domain, setDomain] = useState("executive");
  const { data } = useDashboard(domain, "current_month");

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label>Domain</Label>
        <Select value={domain} onValueChange={setDomain}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DASHBOARD_DOMAINS.map((d) => (
              <SelectItem key={d} value={d}>
                {humanize(d)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        disabled={!data || pending}
        onClick={() =>
          data &&
          onSubmit({
            domain,
            window: data.window_code,
            metrics: data.metrics.map((m) => ({
              metric_code: m.metric_code,
              display_name: m.display_name,
              value: m.value,
              comparison_value: m.comparison_value,
              change_pct: m.change_pct,
            })),
          })
        }
      >
        <Sparkles className="size-4" />
        {pending ? "Requesting…" : "Summarize this month"}
      </Button>
    </div>
  );
}

function MetricChangeForm({
  onSubmit,
  pending,
}: {
  onSubmit: (params: Record<string, unknown>) => void;
  pending: boolean;
}) {
  const { data: metrics } = useMetricCatalog();
  const [metricCode, setMetricCode] = useState("");
  const domain = metrics?.find((m) => m.code === metricCode)?.domain ?? "";
  const { data: dashboard } = useDashboard(domain, "current_month");
  const result = dashboard?.metrics.find((m) => m.metric_code === metricCode);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label>Metric</Label>
        <Select value={metricCode} onValueChange={setMetricCode}>
          <SelectTrigger>
            <SelectValue placeholder="Choose a metric" />
          </SelectTrigger>
          <SelectContent>
            {metrics?.map((m) => (
              <SelectItem key={m.code} value={m.code}>
                {m.display_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        disabled={!result || pending}
        onClick={() =>
          result &&
          onSubmit({
            metric_code: result.metric_code,
            value: result.value,
            comparison_value: result.comparison_value,
            change_pct: result.change_pct,
            window: result.window_code,
          })
        }
      >
        <Sparkles className="size-4" />
        {pending ? "Requesting…" : "Explain this change"}
      </Button>
    </div>
  );
}

function AnomalyEvidenceForm({
  onSubmit,
  pending,
}: {
  onSubmit: (params: Record<string, unknown>) => void;
  pending: boolean;
}) {
  const { data: findings } = useAnomalyFindingList({ page: 1, pageSize: 20, status: "open" });
  const [findingId, setFindingId] = useState("");
  const finding = findings?.data.find((f) => f.id === findingId);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label>Open finding</Label>
        <Select value={findingId} onValueChange={setFindingId}>
          <SelectTrigger>
            <SelectValue placeholder="Choose a finding" />
          </SelectTrigger>
          <SelectContent>
            {findings?.data.map((f) => (
              <SelectItem key={f.id} value={f.id}>
                {humanize(f.metric_code)} — {humanize(f.severity)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        disabled={!finding || pending}
        onClick={() =>
          finding &&
          onSubmit({
            metric_code: finding.metric_code,
            observed_value: finding.observed_value,
            expected_value: finding.expected_value,
            evidence: finding.evidence ?? {},
          })
        }
      >
        <Sparkles className="size-4" />
        {pending ? "Requesting…" : "Summarize this finding"}
      </Button>
    </div>
  );
}

function ReportNarrativeForm({
  onSubmit,
  pending,
}: {
  onSubmit: (params: Record<string, unknown>) => void;
  pending: boolean;
}) {
  const { data: runs } = useReportRunList({ page: 1, pageSize: 20 });
  const completedRuns = runs?.data.filter((r) => r.status === "completed") ?? [];
  const [runId, setRunId] = useState("");
  const run = completedRuns.find((r) => r.id === runId);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label>Completed run</Label>
        <Select value={runId} onValueChange={setRunId}>
          <SelectTrigger>
            <SelectValue placeholder="Choose a report run" />
          </SelectTrigger>
          <SelectContent>
            {completedRuns.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                {humanize(r.window_code)} — {r.id.slice(0, 8)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <Button
        disabled={!run || pending}
        onClick={() =>
          run &&
          onSubmit({
            report_name: run.window_code,
            window: run.window_code,
            metrics: [],
          })
        }
      >
        <Sparkles className="size-4" />
        {pending ? "Requesting…" : "Draft narrative"}
      </Button>
    </div>
  );
}

function QuestionForm({
  onSubmit,
  pending,
}: {
  onSubmit: (params: Record<string, unknown>) => void;
  pending: boolean;
}) {
  const { data: metrics } = useMetricCatalog();
  const [question, setQuestion] = useState("");

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="ai-question">Question</Label>
        <Textarea
          id="ai-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Which metric shows how sales are trending this month?"
        />
      </div>
      <Button
        disabled={!question.trim() || !metrics || pending}
        onClick={() =>
          onSubmit({
            question: question.trim(),
            available_metric_codes: metrics?.map((m) => m.code) ?? [],
          })
        }
      >
        <Sparkles className="size-4" />
        {pending ? "Asking…" : "Ask"}
      </Button>
    </div>
  );
}

function AiResultCard({ requestId }: { requestId: string }) {
  const { data: request, isLoading } = useAiRequestDetail(requestId);
  const submitFeedback = useSubmitAiFeedback(requestId);
  const [feedbackSent, setFeedbackSent] = useState<AiRequestFeedbackInput["outcome_state"] | null>(null);

  return (
    <SectionCard
      title="Result"
      actions={
        <div className="flex items-center gap-2 text-muted-foreground">
          <Bot className="size-4" />
        </div>
      }
    >
      {isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : !request ? (
        <EmptyState title="No result" />
      ) : (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <StatusBadge label={humanize(request.status)} tone={STATUS_TONE[request.status] ?? "neutral"} />
            {request.safety_blocked && (
              <StatusBadge label="Safety blocked" tone="danger" />
            )}
            <span className="text-muted-foreground text-xs">
              {request.provider_code} · {request.model_reference}
            </span>
          </div>

          {request.status === "failed" && (
            <p className="text-destructive text-sm">
              {request.failure_category ? humanize(request.failure_category) : "This request failed."}
            </p>
          )}
          {request.safety_blocked && request.safety_block_reason && (
            <p className="text-destructive text-sm">{request.safety_block_reason}</p>
          )}

          {request.output_structured && (
            <div className="flex flex-col gap-2 rounded-md border p-3 text-sm">
              {Object.entries(request.output_structured).map(([key, value]) => (
                <div key={key}>
                  <p className="text-muted-foreground text-xs">{humanize(key)}</p>
                  <p>{Array.isArray(value) ? value.join(", ") : String(value)}</p>
                </div>
              ))}
            </div>
          )}

          {request.status === "completed" && !feedbackSent && (
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground text-xs">Was this useful?</span>
              <Button
                size="sm"
                variant="outline"
                disabled={submitFeedback.isPending}
                onClick={() =>
                  submitFeedback.mutate(
                    { outcome_state: "accepted" },
                    { onSuccess: () => setFeedbackSent("accepted") },
                  )
                }
              >
                <ThumbsUp className="size-3.5" />
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={submitFeedback.isPending}
                onClick={() =>
                  submitFeedback.mutate(
                    { outcome_state: "rejected" },
                    { onSuccess: () => setFeedbackSent("rejected") },
                  )
                }
              >
                <ThumbsDown className="size-3.5" />
              </Button>
            </div>
          )}
          {feedbackSent && <p className="text-muted-foreground text-xs">Thanks for the feedback.</p>}
        </div>
      )}
    </SectionCard>
  );
}
