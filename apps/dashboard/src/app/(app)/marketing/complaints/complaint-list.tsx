"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Complaint } from "@rkpr/contracts";
import { Plus } from "lucide-react";
import Link from "next/link";

import { useComplaintList } from "@/lib/hooks/use-complaints";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  COMPLAINT_SEVERITY_TONES,
  COMPLAINT_STATUS_TONES,
  formatDateTime,
  humanize,
} from "@/lib/crm-display";
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
import { CreateComplaintModal } from "./create-complaint-modal";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = [
  "new",
  "acknowledged",
  "investigating",
  "awaiting_customer",
  "awaiting_internal",
  "resolution_proposed",
  "resolved",
  "closed",
  "reopened",
  "cancelled",
];
const SEVERITIES = ["low", "medium", "high", "critical"];

export function ComplaintList() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState(ALL);
  const [severityFilter, setSeverityFilter] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const canCreate = hasPermission(currentUser, "complaints.create");

  const { data, isLoading, isError, refetch } = useComplaintList({
    page,
    pageSize: PAGE_SIZE,
    status: statusFilter === ALL ? undefined : statusFilter,
    severity: severityFilter === ALL ? undefined : severityFilter,
  });

  const columns = useMemo<ColumnDef<Complaint, unknown>[]>(
    () => [
      {
        id: "complaint_number",
        header: "Complaint",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/marketing/complaints/${row.original.id}`}
            className="font-medium hover:underline"
          >
            <div className="flex flex-col">
              <span>{row.original.complaint_number}</span>
              <span className="text-muted-foreground max-w-xs truncate text-xs">
                {row.original.title}
              </span>
            </div>
          </Link>
        ),
      },
      {
        id: "category",
        header: "Category",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.category)}</span>,
      },
      {
        id: "severity",
        header: "Severity",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.severity)}
            tone={COMPLAINT_SEVERITY_TONES[row.original.severity]}
          />
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-1">
            <StatusBadge
              label={humanize(row.original.status)}
              tone={COMPLAINT_STATUS_TONES[row.original.status]}
            />
            {row.original.current_escalation_level > 0 && (
              <StatusBadge
                label={`Escalated L${row.original.current_escalation_level}`}
                tone="danger"
              />
            )}
          </div>
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

  const hasActiveFilters = statusFilter !== ALL || severityFilter !== ALL;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <FilterBar
          search=""
          onSearchChange={() => undefined}
          hasActiveFilters={hasActiveFilters}
          onReset={() => {
            setStatusFilter(ALL);
            setSeverityFilter(ALL);
            setPage(1);
          }}
          filters={
            <>
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
              <Select
                value={severityFilter}
                onValueChange={(v) => {
                  setSeverityFilter(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-36" aria-label="Filter by severity">
                  <SelectValue placeholder="Severity" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>All severities</SelectItem>
                  {SEVERITIES.map((severity) => (
                    <SelectItem key={severity} value={severity}>
                      {humanize(severity)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          }
        />
        {canCreate && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="size-4" />
            New complaint
          </Button>
        )}
      </div>

      {isError ? (
        <ErrorState title="Could not load complaints" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No complaints match these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters."
              : "Complaints raised directly or converted from feedback will appear here."
          }
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: data?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      )}

      <CreateComplaintModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
