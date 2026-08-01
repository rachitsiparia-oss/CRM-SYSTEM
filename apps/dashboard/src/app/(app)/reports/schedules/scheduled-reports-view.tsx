"use client";

import { useState } from "react";
import type { ExportFormat, ScheduleFrequency, ScheduledReport } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import {
  useAddScheduledReportRecipient,
  useRunScheduledReportNow,
  useCreateScheduledReport,
  useScheduledReportDeliveryAttempts,
  useScheduledReportList,
  useScheduledReportRecipients,
  useSetScheduledReportEnabled,
} from "@/lib/hooks/use-report-schedules";
import { useReportDefinitionList } from "@/lib/hooks/use-reports";
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
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

const DELIVERY_STATUS_TONE: Record<string, "neutral" | "info" | "success" | "warning" | "danger"> = {
  pending: "neutral",
  sent: "info",
  delivered: "success",
  failed: "danger",
};

export function ScheduledReportsView() {
  const [page] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [selected, setSelected] = useState<ScheduledReport | null>(null);
  const { data: schedules, isLoading } = useScheduledReportList(page, 20);

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Scheduled Reports"
        description="Recurring report delivery to staff, roles, or override addresses."
        actions={
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="size-4" />
            New schedule
          </Button>
        }
      />

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : !schedules || schedules.data.length === 0 ? (
        <EmptyState
          title="No scheduled reports"
          description="Schedule a saved report to have it generated and delivered automatically."
          action={<Button onClick={() => setShowCreate(true)}>New schedule</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {schedules.data.map((schedule) => (
            <SectionCard
              key={schedule.id}
              title={schedule.name}
              description={`${humanize(schedule.schedule_frequency)} · ${schedule.schedule_time_of_day} ${schedule.timezone}`}
              actions={
                <StatusBadge
                  label={schedule.is_enabled ? "Enabled" : "Disabled"}
                  tone={schedule.is_enabled ? "success" : "neutral"}
                />
              }
            >
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-xs">
                  Output: {schedule.output_format.toUpperCase()}
                </span>
                <Button size="sm" variant="ghost" onClick={() => setSelected(schedule)}>
                  Manage
                </Button>
              </div>
            </SectionCard>
          ))}
        </div>
      )}

      <CreateScheduleModal open={showCreate} onOpenChange={setShowCreate} />
      {selected && (
        <ScheduleDetailModal schedule={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function CreateScheduleModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: definitions } = useReportDefinitionList({ page: 1, pageSize: 100 });
  const [reportDefinitionId, setReportDefinitionId] = useState("");
  const [name, setName] = useState("");
  const [frequency, setFrequency] = useState<ScheduleFrequency>("weekly");
  const [dayOfWeek, setDayOfWeek] = useState("1");
  const [dayOfMonth, setDayOfMonth] = useState("1");
  const [timeOfDay, setTimeOfDay] = useState("08:00");
  const [outputFormat, setOutputFormat] = useState<ExportFormat>("pdf");
  const [error, setError] = useState<string | null>(null);
  const createSchedule = useCreateScheduledReport();

  const reset = () => {
    setReportDefinitionId("");
    setName("");
    setFrequency("weekly");
    setDayOfWeek("1");
    setDayOfMonth("1");
    setTimeOfDay("08:00");
    setOutputFormat("pdf");
    setError(null);
  };

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New scheduled report"
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!reportDefinitionId || !name.trim() || createSchedule.isPending}
            onClick={() => {
              setError(null);
              createSchedule.mutate(
                {
                  report_definition_id: reportDefinitionId,
                  name: name.trim(),
                  schedule_frequency: frequency,
                  schedule_day_of_week: frequency === "weekly" ? Number(dayOfWeek) : null,
                  schedule_day_of_month: frequency === "monthly" ? Number(dayOfMonth) : null,
                  schedule_time_of_day: timeOfDay,
                  output_format: outputFormat,
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create this schedule."),
                },
              );
            }}
          >
            {createSchedule.isPending ? "Creating…" : "Create schedule"}
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
          <Label>Report</Label>
          <Select value={reportDefinitionId} onValueChange={setReportDefinitionId}>
            <SelectTrigger>
              <SelectValue placeholder="Choose a saved report" />
            </SelectTrigger>
            <SelectContent>
              {definitions?.data.map((d) => (
                <SelectItem key={d.id} value={d.id}>
                  {d.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="schedule-name">Schedule name</Label>
          <Input id="schedule-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Frequency</Label>
            <Select value={frequency} onValueChange={(v) => setFrequency(v as ScheduleFrequency)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="schedule-time">Time of day</Label>
            <Input
              id="schedule-time"
              type="time"
              value={timeOfDay}
              onChange={(e) => setTimeOfDay(e.target.value)}
            />
          </div>
        </div>
        {frequency === "weekly" && (
          <div className="flex flex-col gap-1.5">
            <Label>Day of week</Label>
            <Select value={dayOfWeek} onValueChange={setDayOfWeek}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].map(
                  (day, i) => (
                    <SelectItem key={day} value={String(i)}>
                      {day}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
          </div>
        )}
        {frequency === "monthly" && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="schedule-dom">Day of month</Label>
            <Input
              id="schedule-dom"
              type="number"
              min={1}
              max={28}
              value={dayOfMonth}
              onChange={(e) => setDayOfMonth(e.target.value)}
            />
          </div>
        )}
        <div className="flex flex-col gap-1.5">
          <Label>Output format</Label>
          <Select value={outputFormat} onValueChange={(v) => setOutputFormat(v as ExportFormat)}>
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
      </div>
    </Modal>
  );
}

function ScheduleDetailModal({
  schedule,
  onClose,
}: {
  schedule: ScheduledReport;
  onClose: () => void;
}) {
  const [emailOverride, setEmailOverride] = useState("");
  const setEnabled = useSetScheduledReportEnabled(schedule.id);
  const runNow = useRunScheduledReportNow(schedule.id);
  const addRecipient = useAddScheduledReportRecipient(schedule.id);
  const { data: recipients } = useScheduledReportRecipients(schedule.id);
  const { data: attempts } = useScheduledReportDeliveryAttempts(schedule.id, 1, 10);

  return (
    <Modal open onOpenChange={(open) => !open && onClose()} title={schedule.name} size="lg">
      <div className="flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <span className="text-sm">Enabled</span>
          <Switch
            checked={schedule.is_enabled}
            onCheckedChange={(checked) => setEnabled.mutate({ is_enabled: checked })}
          />
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-medium">Recipients</h3>
            <Button size="sm" onClick={() => runNow.mutate()} disabled={runNow.isPending}>
              {runNow.isPending ? "Running…" : "Run now"}
            </Button>
          </div>
          <div className="flex flex-col gap-1.5">
            {(recipients ?? []).map((r) => (
              <p key={r.id} className="text-muted-foreground text-sm">
                {r.recipient_email_override ?? r.recipient_role_code ?? r.recipient_staff_id}
              </p>
            ))}
            {(!recipients || recipients.length === 0) && (
              <p className="text-muted-foreground text-sm">No recipients configured.</p>
            )}
          </div>
          <div className="mt-2 flex gap-2">
            <Input
              placeholder="email@example.com"
              value={emailOverride}
              onChange={(e) => setEmailOverride(e.target.value)}
            />
            <Button
              variant="outline"
              disabled={!emailOverride.trim() || addRecipient.isPending}
              onClick={() =>
                addRecipient.mutate(
                  { recipient_email_override: emailOverride.trim() },
                  { onSuccess: () => setEmailOverride("") },
                )
              }
            >
              Add
            </Button>
          </div>
        </div>

        <div>
          <h3 className="mb-2 text-sm font-medium">Delivery history</h3>
          {!attempts || attempts.data.length === 0 ? (
            <p className="text-muted-foreground text-sm">No delivery attempts yet.</p>
          ) : (
            <div className="flex flex-col gap-2">
              {attempts.data.map((attempt) => (
                <div
                  key={attempt.id}
                  className="flex items-center justify-between rounded-md border p-2 text-sm"
                >
                  <span>{attempt.recipient_reference}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground text-xs">
                      {formatDateTime(attempt.attempted_at)}
                    </span>
                    <StatusBadge
                      label={humanize(attempt.status)}
                      tone={DELIVERY_STATUS_TONE[attempt.status] ?? "neutral"}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
