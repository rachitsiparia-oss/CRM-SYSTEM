"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { JobQueueName, JobRecord, JobStatus } from "@rkpr/contracts";

import { useCancelJob, useJobList } from "@/lib/hooks/use-jobs";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { humanize, formatDateTime } from "@/lib/crm-display";
import type { StatusTone } from "@/components/status-badge";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const JOB_STATUSES: JobStatus[] = [
  "scheduled",
  "pending",
  "queued",
  "running",
  "retry_wait",
  "succeeded",
  "failed_permanent",
  "cancelled",
  "dead_lettered",
];
const JOB_QUEUE_NAMES: JobQueueName[] = [
  "critical-domain",
  "communications",
  "campaigns",
  "reports",
  "exports",
  "integrations",
  "ai",
  "maintenance",
];
const JOB_STATUS_TONE: Record<JobStatus, StatusTone> = {
  scheduled: "neutral",
  pending: "neutral",
  queued: "neutral",
  running: "info",
  retry_wait: "warning",
  succeeded: "success",
  failed_permanent: "danger",
  cancelled: "neutral",
  dead_lettered: "danger",
};
const CANCELLABLE_STATUSES: JobStatus[] = ["pending", "scheduled", "retry_wait"];
const PAGE_SIZE = 25;

export function JobsView() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "jobs.manage");
  const [status, setStatus] = useState<string>("all");
  const [queueName, setQueueName] = useState<string>("all");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useJobList({
    status: status === "all" ? undefined : status,
    queueName: queueName === "all" ? undefined : queueName,
    page,
    pageSize: PAGE_SIZE,
  });
  const cancelJob = useCancelJob();

  const columns = useMemo<ColumnDef<JobRecord, unknown>[]>(
    () => [
      {
        id: "job_type",
        header: "Job type",
        enableSorting: false,
        cell: ({ row }) => <span className="font-mono text-xs">{row.original.job_type}</span>,
      },
      {
        id: "queue_name",
        header: "Queue",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.queue_name}</span>,
      },
      {
        id: "priority",
        header: "Priority",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.priority)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={JOB_STATUS_TONE[row.original.status]}
          />
        ),
      },
      {
        id: "attempts",
        header: "Attempts",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.attempts} / {row.original.max_attempts}
          </span>
        ),
      },
      {
        id: "started_at",
        header: "Started",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">
            {formatDateTime(row.original.started_at)}
          </span>
        ),
      },
      {
        id: "failure_message",
        header: "Failure",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground max-w-xs truncate text-sm">
            {row.original.failure_message ?? "—"}
          </span>
        ),
      },
      ...(canManage
        ? [
            {
              id: "actions",
              header: "",
              enableSorting: false,
              cell: ({ row }: { row: { original: JobRecord } }) =>
                CANCELLABLE_STATUSES.includes(row.original.status) ? (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={cancelJob.isPending}
                    onClick={() => cancelJob.mutate(row.original.id)}
                  >
                    Cancel
                  </Button>
                ) : null,
            } satisfies ColumnDef<JobRecord, unknown>,
          ]
        : []),
    ],
    [canManage, cancelJob],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Jobs"
        description="Durable execution record for every background job — ARQ and Redis coordinate execution, this table is the source of truth."
      />

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {JOB_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {humanize(s)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={queueName}
          onValueChange={(v) => {
            setQueueName(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Queue" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All queues</SelectItem>
            {JOB_QUEUE_NAMES.map((q) => (
              <SelectItem key={q} value={q}>
                {q}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.data ?? []}
        getRowId={(row) => row.id}
        loading={isLoading}
        emptyTitle="No jobs found"
        emptyDescription="No job records match these filters yet."
        pagination={
          data
            ? {
                pageIndex: page - 1,
                pageCount: Math.max(1, Math.ceil(data.pagination.total / data.pagination.page_size)),
                total: data.pagination.total,
                pageSize: data.pagination.page_size,
                onPageChange: (pageIndex) => setPage(pageIndex + 1),
              }
            : undefined
        }
      />
    </div>
  );
}
