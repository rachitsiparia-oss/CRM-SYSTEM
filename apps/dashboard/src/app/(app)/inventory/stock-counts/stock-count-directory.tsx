"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { StockCountListItem } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useInventoryStockCounts } from "@/lib/hooks/use-inventory-operations";
import { useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { COUNT_STATUS_TONES, formatDate, formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
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
import { StockCountCreateModal } from "./stock-count-create-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

export function StockCountDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const { data: locations } = useInventoryLocations();
  const { data, isLoading, isError, refetch } = useInventoryStockCounts(
    page,
    PAGE_SIZE,
    status === ALL ? undefined : status,
  );

  const canCreate = hasPermission(currentUser, "inventory.counts.create");
  const locationName = useMemo(
    () => new Map((locations ?? []).map((l) => [l.id, l.name])),
    [locations],
  );

  const columns = useMemo<ColumnDef<StockCountListItem, unknown>[]>(
    () => [
      {
        id: "count_number",
        header: "Count",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/inventory/stock-counts/${row.original.id}`}
            className="font-medium hover:underline"
          >
            {row.original.count_number}
          </Link>
        ),
      },
      {
        id: "location",
        header: "Location",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {locationName.get(row.original.storage_location_id) ?? "—"}
          </span>
        ),
      },
      {
        id: "scheduled_date",
        header: "Scheduled",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDate(row.original.scheduled_date)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={COUNT_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "created_at",
        header: "Created",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.created_at)}</span>,
      },
    ],
    [locationName],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Stock Counts"
        description="Physical cycle counts — variance is reviewed and approved before the ledger is corrected."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New stock count
            </Button>
          ) : null
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={status}
          onValueChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-44" aria-label="Filter by status">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="in_progress">In progress</SelectItem>
            <SelectItem value="submitted">Submitted</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isError ? (
        <ErrorState title="Could not load stock counts" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No stock counts yet"
          emptyDescription="Start a cycle count session for a location."
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: data?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      )}

      <StockCountCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
