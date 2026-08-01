"use client";

import { useState } from "react";
import type {
  AnomalyComparisonOperator,
  AnomalyFinding,
  AnomalyFindingStatus,
  AnomalyRuleType,
  AnomalySeverity,
} from "@rkpr/contracts";
import { Plus, RefreshCw } from "lucide-react";

import {
  useAnomalyFindingList,
  useAnomalyRuleList,
  useCreateAnomalyRule,
  useEvaluateAnomalyRules,
  useTransitionAnomalyFinding,
} from "@/lib/hooks/use-anomalies";
import { useMetricCatalog } from "@/lib/hooks/use-reports";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const RULE_TYPES: AnomalyRuleType[] = [
  "absolute_threshold",
  "pct_change_prior_period",
  "rolling_average_deviation",
  "count_rate_threshold",
  "consecutive_deterioration",
  "missing_activity",
];
const COMPARISON_OPERATORS: AnomalyComparisonOperator[] = ["gt", "gte", "lt", "lte"];
const SEVERITIES: AnomalySeverity[] = ["low", "medium", "high", "critical"];
const SEVERITY_TONE: Record<AnomalySeverity, "neutral" | "warning" | "danger"> = {
  low: "neutral",
  medium: "warning",
  high: "danger",
  critical: "danger",
};
const NEXT_STATUSES: Record<AnomalyFindingStatus, AnomalyFindingStatus[]> = {
  open: ["acknowledged", "dismissed"],
  acknowledged: ["investigating", "resolved", "dismissed"],
  investigating: ["resolved", "dismissed"],
  resolved: [],
  dismissed: [],
};

export function AnomalyCenterView() {
  const [showCreateRule, setShowCreateRule] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("open");
  const { data: rules, isLoading: rulesLoading } = useAnomalyRuleList();
  const { data: findings, isLoading: findingsLoading } = useAnomalyFindingList({
    page: 1,
    pageSize: 20,
    status: statusFilter === "all" ? undefined : statusFilter,
  });
  const evaluate = useEvaluateAnomalyRules();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Anomaly Center"
        description="Deterministic anomaly rules and the findings they produce."
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => evaluate.mutate()} disabled={evaluate.isPending}>
              <RefreshCw className="size-4" />
              {evaluate.isPending ? "Evaluating…" : "Evaluate now"}
            </Button>
            <Button onClick={() => setShowCreateRule(true)}>
              <Plus className="size-4" />
              New rule
            </Button>
          </div>
        }
      />

      <SectionCard title="Rules" description="Active and inactive anomaly detection rules.">
        {rulesLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : !rules || rules.length === 0 ? (
          <EmptyState title="No rules configured" />
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {rules.map((rule) => (
              <div key={rule.id} className="flex flex-col gap-1 rounded-md border p-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{rule.name}</span>
                  <StatusBadge label={humanize(rule.severity)} tone={SEVERITY_TONE[rule.severity]} />
                </div>
                <span className="text-muted-foreground text-xs">
                  {rule.metric_code} · {humanize(rule.rule_type)}
                </span>
                <StatusBadge
                  label={rule.is_active ? "Active" : "Inactive"}
                  tone={rule.is_active ? "success" : "neutral"}
                  className="w-fit"
                />
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard
        title="Findings"
        description="Detected anomalies, most recent first."
        actions={
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="acknowledged">Acknowledged</SelectItem>
              <SelectItem value="investigating">Investigating</SelectItem>
              <SelectItem value="resolved">Resolved</SelectItem>
              <SelectItem value="dismissed">Dismissed</SelectItem>
            </SelectContent>
          </Select>
        }
      >
        {findingsLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : !findings || findings.data.length === 0 ? (
          <EmptyState title="No findings" description="No anomalies match this filter." />
        ) : (
          <div className="flex flex-col gap-2">
            {findings.data.map((finding) => (
              <FindingRow key={finding.id} finding={finding} />
            ))}
          </div>
        )}
      </SectionCard>

      <CreateRuleModal open={showCreateRule} onOpenChange={setShowCreateRule} />
    </div>
  );
}

function FindingRow({ finding }: { finding: AnomalyFinding }) {
  const transition = useTransitionAnomalyFinding(finding.id);
  const nextStatuses = NEXT_STATUSES[finding.status] ?? [];

  return (
    <div className="flex items-center justify-between gap-3 rounded-md border p-3 text-sm">
      <div className="flex flex-col">
        <span className="font-medium">{humanize(finding.metric_code)}</span>
        <span className="text-muted-foreground text-xs">
          {formatDateTime(finding.observed_window_end)} · observed{" "}
          {finding.observed_value ?? "—"}, expected {finding.expected_value ?? "—"}
          {finding.deviation_pct !== null && ` (${finding.deviation_pct.toFixed(1)}% deviation)`}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge label={humanize(finding.severity)} tone={SEVERITY_TONE[finding.severity]} />
        <StatusBadge label={humanize(finding.status)} tone="neutral" />
        {nextStatuses.map((status) => (
          <Button
            key={status}
            size="sm"
            variant="outline"
            disabled={transition.isPending}
            onClick={() => transition.mutate({ target_status: status })}
          >
            {humanize(status)}
          </Button>
        ))}
      </div>
    </div>
  );
}

function CreateRuleModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: metrics } = useMetricCatalog();
  const createRule = useCreateAnomalyRule();
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [metricCode, setMetricCode] = useState("");
  const [ruleType, setRuleType] = useState<AnomalyRuleType>("absolute_threshold");
  const [comparisonOperator, setComparisonOperator] = useState<AnomalyComparisonOperator>("gt");
  const [thresholdValue, setThresholdValue] = useState("");
  const [severity, setSeverity] = useState<AnomalySeverity>("medium");
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setCode("");
    setName("");
    setMetricCode("");
    setRuleType("absolute_threshold");
    setComparisonOperator("gt");
    setThresholdValue("");
    setSeverity("medium");
    setError(null);
  };

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New anomaly rule"
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!code.trim() || !name.trim() || !metricCode || createRule.isPending}
            onClick={() => {
              setError(null);
              createRule.mutate(
                {
                  code: code.trim(),
                  name: name.trim(),
                  metric_code: metricCode,
                  rule_type: ruleType,
                  comparison_operator: comparisonOperator,
                  threshold_value: thresholdValue.trim() ? Number(thresholdValue) : null,
                  severity,
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create this rule."),
                },
              );
            }}
          >
            {createRule.isPending ? "Creating…" : "Create rule"}
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
            <Label htmlFor="rule-code">Code</Label>
            <Input id="rule-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-name">Name</Label>
            <Input id="rule-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>

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

        <div className="grid grid-cols-3 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Rule type</Label>
            <Select value={ruleType} onValueChange={(v) => setRuleType(v as AnomalyRuleType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RULE_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {humanize(type)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Comparison</Label>
            <Select
              value={comparisonOperator}
              onValueChange={(v) => setComparisonOperator(v as AnomalyComparisonOperator)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COMPARISON_OPERATORS.map((op) => (
                  <SelectItem key={op} value={op}>
                    {op}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-threshold">Threshold</Label>
            <Input
              id="rule-threshold"
              type="number"
              value={thresholdValue}
              onChange={(e) => setThresholdValue(e.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Severity</Label>
          <Select value={severity} onValueChange={(v) => setSeverity(v as AnomalySeverity)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SEVERITIES.map((s) => (
                <SelectItem key={s} value={s}>
                  {humanize(s)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </Modal>
  );
}
