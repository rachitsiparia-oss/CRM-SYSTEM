"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { MovementType, StockMovement } from "@rkpr/contracts";

import { useInventoryItemList, useInventoryMovements } from "@/lib/hooks/use-inventory-items";
import { useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { formatDateTime, formatQuantity, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";

const PAGE_SIZE = 50;
const ALL = "__all";

const MOVEMENT_TYPES: MovementType[] = [
  "opening_balance",
  "purchase_receipt",
  "order_reservation",
  "reservation_release",
  "order_consumption",
  "wastage",
  "positive_adjustment",
  "negative_adjustment",
  "transfer_out",
  "transfer_in",
  "supplier_return",
  "customer_return",
  "stock_count_adjustment",
  "reversal",
];

export function MovementLedger() {
  const [page, setPage] = useState(1);
  const [movementType, setMovementType] = useState(ALL);
  const [itemId, setItemId] = useState(ALL);
  const [locationId, setLocationId] = useState(ALL);

  const { data: items } = useInventoryItemList({ page: 1, pageSize: 200, sort: "name" });
  const { data: locations } = useInventoryLocations();

  const { data, isLoading, isError, refetch } = useInventoryMovements({
    page,
    pageSize: PAGE_SIZE,
    movementType: movementType === ALL ? undefined : movementType,
    inventoryItemId: itemId === ALL ? undefined : itemId,
    storageLocationId: locationId === ALL ? undefined : locationId,
  });

  const itemName = useMemo(() => new Map((items?.data ?? []).map((i) => [i.id, i.name])), [items]);
  const locationName = useMemo(
    () => new Map((locations ?? []).map((l) => [l.id, l.name])),
    [locations],
  );

  const columns = useMemo<ColumnDef<StockMovement, unknown>[]>(
    () => [
      {
        id: "movement_number",
        header: "Movement",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="font-mono text-xs">{row.original.movement_number}</span>
        ),
      },
      {
        id: "item",
        header: "Item",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{itemName.get(row.original.inventory_item_id) ?? "—"}</span>
        ),
      },
      {
        id: "location",
        header: "Location",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{locationName.get(row.original.storage_location_id) ?? "—"}</span>
        ),
      },
      {
        id: "movement_type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.movement_type)}</span>,
      },
      {
        id: "quantity_delta",
        header: "Quantity",
        enableSorting: false,
        cell: ({ row }) => (
          <span className={Number(row.original.quantity_delta) < 0 ? "text-destructive" : undefined}>
            {formatQuantity(row.original.quantity_delta)}
          </span>
        ),
      },
      {
        id: "occurred_at",
        header: "Occurred",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.occurred_at)}</span>,
      },
      {
        id: "reversed",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (row.original.reversed_at ? <span className="text-xs">Reversed</span> : null),
      },
    ],
    [itemName, locationName],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const hasActiveFilters = movementType !== ALL || itemId !== ALL || locationId !== ALL;

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Movement Ledger"
        description="The immutable, append-only stock ledger — every change to every item, ever."
      />

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={movementType}
          onValueChange={(value) => {
            setMovementType(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-48" aria-label="Filter by movement type">
            <SelectValue placeholder="Movement type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All types</SelectItem>
            {MOVEMENT_TYPES.map((type) => (
              <SelectItem key={type} value={type}>
                {humanize(type)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={itemId}
          onValueChange={(value) => {
            setItemId(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-48" aria-label="Filter by item">
            <SelectValue placeholder="Item" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All items</SelectItem>
            {(items?.data ?? []).map((item) => (
              <SelectItem key={item.id} value={item.id}>
                {item.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={locationId}
          onValueChange={(value) => {
            setLocationId(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-44" aria-label="Filter by location">
            <SelectValue placeholder="Location" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>All locations</SelectItem>
            {(locations ?? []).map((location) => (
              <SelectItem key={location.id} value={location.id}>
                {location.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setMovementType(ALL);
              setItemId(ALL);
              setLocationId(ALL);
              setPage(1);
            }}
          >
            Reset
          </Button>
        )}
      </div>

      {isError ? (
        <ErrorState title="Could not load the movement ledger" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No movements match these filters"
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
