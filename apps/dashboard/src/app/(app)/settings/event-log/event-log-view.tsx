"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { OutboxEvent } from "@rkpr/contracts";

import { useEventLogList } from "@/lib/hooks/use-event-log";
import { humanize, formatDateTime } from "@/lib/crm-display";
import type { StatusTone } from "@/components/status-badge";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/status-badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SearchInput } from "@/components/forms/search-input";

const EVENT_STATUSES = [
  "pending",
  "processing",
  "published",
  "failed_retryable",
  "failed_permanent",
  "cancelled",
] as const;
const EVENT_STATUS_TONE: Record<(typeof EVENT_STATUSES)[number], StatusTone> = {
  pending: "neutral",
  processing: "info",
  published: "success",
  failed_retryable: "warning",
  failed_permanent: "danger",
  cancelled: "neutral",
};
const PAGE_SIZE = 25;

export function EventLogView() {
  const [status, setStatus] = useState<string>("all");
  const [eventType, setEventType] = useState("");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useEventLogList({
    status: status === "all" ? undefined : status,
    eventType: eventType.trim() || undefined,
    page,
    pageSize: PAGE_SIZE,
  });

  const columns = useMemo<ColumnDef<OutboxEvent, unknown>[]>(
    () => [
      {
        id: "event_type",
        header: "Event type",
        enableSorting: false,
        cell: ({ row }) => <span className="font-mono text-xs">{row.original.event_type}</span>,
      },
      {
        id: "aggregate_type",
        header: "Aggregate",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.aggregate_type)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={
              EVENT_STATUS_TONE[row.original.status as (typeof EVENT_STATUSES)[number]] ?? "neutral"
            }
          />
        ),
      },
      {
        id: "attempts",
        header: "Attempts",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.attempts}</span>,
      },
      {
        id: "available_at",
        header: "Available at",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">
            {formatDateTime(row.original.available_at)}
          </span>
        ),
      },
      {
        id: "last_error",
        header: "Last error",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground max-w-xs truncate text-sm">
            {row.original.last_error ?? "—"}
          </span>
        ),
      },
    ],
    [],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Event Log"
        description="The domain event / outbox publication log — every event a module has produced and how it was consumed."
      />

      <div className="flex flex-wrap items-center gap-2">
        <SearchInput
          value={eventType}
          onChange={(value) => {
            setEventType(value);
            setPage(1);
          }}
          placeholder="Filter by event type…"
          className="max-w-xs"
        />
        <Select
          value={status}
          onValueChange={(v) => {
            setStatus(v);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {EVENT_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {humanize(s)}
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
        emptyTitle="No events found"
        emptyDescription="No domain events match these filters yet."
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
