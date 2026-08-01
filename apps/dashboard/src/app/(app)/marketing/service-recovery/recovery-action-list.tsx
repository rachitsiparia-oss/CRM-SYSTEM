"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { RecoveryAction } from "@rkpr/contracts";
import Link from "next/link";

import { useRecoveryActionList } from "@/lib/hooks/use-service-recovery";
import { RECOVERY_STATUS_TONES, formatDateTime, formatMinorUnits, humanize } from "@/lib/crm-display";
import { FilterBar } from "@/components/filter-bar";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
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
  "proposed",
  "approval_required",
  "approved",
  "rejected",
  "executing",
  "completed",
  "failed",
  "reversed",
  "cancelled",
];

export function RecoveryActionList() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState(ALL);

  const { data, isLoading, isError, refetch } = useRecoveryActionList({
    page,
    pageSize: PAGE_SIZE,
    status: statusFilter === ALL ? undefined : statusFilter,
  });

  const columns = useMemo<ColumnDef<RecoveryAction, unknown>[]>(
    () => [
      {
        id: "recovery_type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm font-medium">{humanize(row.original.recovery_type)}</span>
        ),
      },
      {
        id: "value",
        header: "Value",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.value_minor !== null
              ? formatMinorUnits(row.original.value_minor)
              : row.original.points !== null
                ? `${row.original.points} points`
                : "—"}
          </span>
        ),
      },
      {
        id: "description",
        header: "Description",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground max-w-xs truncate text-sm">
            {row.original.description}
          </span>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={RECOVERY_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "complaint",
        header: "Complaint",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/marketing/complaints/${row.original.complaint_id}`}
            className="text-sm hover:underline"
          >
            View complaint
          </Link>
        ),
      },
      {
        id: "proposed_at",
        header: "Proposed",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatDateTime(row.original.proposed_at)}</span>
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
            <SelectTrigger className="w-48" aria-label="Filter by status">
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

      {isError ? (
        <ErrorState title="Could not load recovery actions" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No recovery actions match these filters"
          emptyDescription="Propose a recovery action from a complaint's detail page."
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
