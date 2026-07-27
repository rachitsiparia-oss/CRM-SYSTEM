"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { TransferListItem } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useInventoryTransfers } from "@/lib/hooks/use-inventory-operations";
import { useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { TRANSFER_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
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
import { TransferCreateModal } from "./transfer-create-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

export function TransferDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const { data: locations } = useInventoryLocations();
  const { data, isLoading, isError, refetch } = useInventoryTransfers(
    page,
    PAGE_SIZE,
    status === ALL ? undefined : status,
  );

  const canCreate = hasPermission(currentUser, "inventory.transfers.create");
  const locationName = useMemo(
    () => new Map((locations ?? []).map((l) => [l.id, l.name])),
    [locations],
  );

  const columns = useMemo<ColumnDef<TransferListItem, unknown>[]>(
    () => [
      {
        id: "transfer_number",
        header: "Transfer",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/inventory/transfers/${row.original.id}`}
            className="font-medium hover:underline"
          >
            {row.original.transfer_number}
          </Link>
        ),
      },
      {
        id: "route",
        header: "Route",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {locationName.get(row.original.source_location_id) ?? "—"} →{" "}
            {locationName.get(row.original.destination_location_id) ?? "—"}
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
            tone={TRANSFER_STATUS_TONES[row.original.status]}
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
        title="Stock Transfers"
        description="Internal stock movement between storage locations — always posted as a linked pair."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New transfer
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
          <SelectTrigger className="w-40" aria-label="Filter by status">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All statuses</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="posted">Posted</SelectItem>
            <SelectItem value="reversed">Reversed</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isError ? (
        <ErrorState title="Could not load transfers" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No transfers yet"
          emptyDescription="Create a transfer to move stock between locations."
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: data?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      )}

      <TransferCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
