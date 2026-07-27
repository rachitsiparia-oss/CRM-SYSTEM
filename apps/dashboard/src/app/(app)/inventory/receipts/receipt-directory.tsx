"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { ReceiptListItem } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useInventoryReceipts } from "@/lib/hooks/use-inventory-operations";
import { useInventorySuppliers, useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { RECEIPT_STATUS_TONES, formatDate, formatMinorUnits, humanize } from "@/lib/crm-display";
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
import { ReceiptCreateModal } from "./receipt-create-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

export function ReceiptDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const { data: suppliersPage } = useInventorySuppliers({ pageSize: 100 });
  const { data: locations } = useInventoryLocations();
  const { data, isLoading, isError, refetch } = useInventoryReceipts(
    page,
    PAGE_SIZE,
    status === ALL ? undefined : status,
  );

  const canCreate = hasPermission(currentUser, "inventory.receipts.create");
  const supplierName = useMemo(
    () => new Map((suppliersPage?.data ?? []).map((s) => [s.id, s.name])),
    [suppliersPage],
  );
  const locationName = useMemo(
    () => new Map((locations ?? []).map((l) => [l.id, l.name])),
    [locations],
  );

  const columns = useMemo<ColumnDef<ReceiptListItem, unknown>[]>(
    () => [
      {
        id: "receipt_number",
        header: "Receipt",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/inventory/receipts/${row.original.id}`}
            className="font-medium hover:underline"
          >
            {row.original.receipt_number}
          </Link>
        ),
      },
      {
        id: "supplier",
        header: "Supplier",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{supplierName.get(row.original.supplier_id) ?? "—"}</span>
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
        id: "received_date",
        header: "Received",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDate(row.original.received_date)}</span>,
      },
      {
        id: "total_value_minor",
        header: "Value",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatMinorUnits(row.original.total_value_minor)}</span>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={RECEIPT_STATUS_TONES[row.original.status]}
          />
        ),
      },
    ],
    [supplierName, locationName],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Goods Receipts"
        description="Supplier purchase receipts — draft while lines are entered, posted to update stock and cost."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New receipt
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
        {status !== ALL && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setStatus(ALL);
              setPage(1);
            }}
          >
            Reset
          </Button>
        )}
      </div>

      {isError ? (
        <ErrorState title="Could not load receipts" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No receipts yet"
          emptyDescription="Create a receipt to record stock arriving from a supplier."
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: data?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      )}

      <ReceiptCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
