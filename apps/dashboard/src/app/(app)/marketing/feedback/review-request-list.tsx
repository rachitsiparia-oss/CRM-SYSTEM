"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { ReviewRequest } from "@rkpr/contracts";

import { useProcessPendingReviewRequests, useReviewRequestList } from "@/lib/hooks/use-feedback";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { REVIEW_REQUEST_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { FilterBar } from "@/components/filter-bar";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = [
  "draft",
  "eligible",
  "scheduled",
  "sent",
  "delivered",
  "opened",
  "completed",
  "expired",
  "suppressed",
  "cancelled",
  "failed",
];

export function ReviewRequestList() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState(ALL);

  const canManage = hasPermission(currentUser, "feedback.request_review");
  const processPending = useProcessPendingReviewRequests();

  const { data, isLoading, isError, refetch } = useReviewRequestList({
    page,
    pageSize: PAGE_SIZE,
    status: statusFilter === ALL ? undefined : statusFilter,
  });

  const columns = useMemo<ColumnDef<ReviewRequest, unknown>[]>(
    () => [
      {
        id: "source_type",
        header: "Source",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.source_type)}</span>,
      },
      {
        id: "channel",
        header: "Channel",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.channel)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={REVIEW_REQUEST_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "reason",
        header: "Eligibility / suppression",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-xs">
            {row.original.eligibility_reason ?? row.original.suppression_reason ?? "—"}
          </span>
        ),
      },
      {
        id: "created_at",
        header: "Created",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatDateTime(row.original.created_at)}</span>
        ),
      },
    ],
    [],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <FilterBar
          search=""
          onSearchChange={() => undefined}
          hasActiveFilters={statusFilter !== ALL}
          onReset={() => {
            setStatusFilter(ALL);
            setPage(1);
          }}
          filters={
            <Select
              value={statusFilter}
              onValueChange={(v) => {
                setStatusFilter(v);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44" aria-label="Filter by status">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All statuses</SelectItem>
                {STATUSES.map((status) => (
                  <SelectItem key={status} value={status}>
                    {humanize(status)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          }
        />
        {canManage && (
          <Button
            variant="outline"
            disabled={processPending.isPending}
            onClick={() => processPending.mutate()}
          >
            {processPending.isPending ? "Processing…" : "Process pending"}
          </Button>
        )}
      </div>

      {isError ? (
        <ErrorState title="Could not load review requests" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No review requests match these filters"
          emptyDescription="Review requests are scheduled automatically when an order or reservation completes."
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: data?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      )}
    </div>
  );
}
