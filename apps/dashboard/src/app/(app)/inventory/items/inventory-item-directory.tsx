"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import type { ColumnDef } from "@tanstack/react-table";
import type { InventoryItemListItem } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useInventoryItemList } from "@/lib/hooks/use-inventory-items";
import { useInventoryCategories, useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { STOCK_STATUS_TONES, formatQuantity, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
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
import { InventoryItemCreateModal } from "./inventory-item-create-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "name", label: "Name" },
  { value: "newest", label: "Newest" },
  { value: "oldest", label: "Oldest" },
  { value: "available_quantity", label: "Available quantity" },
  { value: "stock_value", label: "Stock value" },
];

export function InventoryItemDirectory() {
  const { data: currentUser } = useCurrentUser();
  const searchParams = useSearchParams();

  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [categoryId, setCategoryId] = useState(ALL);
  const [locationId, setLocationId] = useState(ALL);
  const [lowStock, setLowStock] = useState(searchParams.get("low_stock") === "true");
  const [outOfStock, setOutOfStock] = useState(searchParams.get("out_of_stock") === "true");
  const [sort, setSort] = useState<
    "name" | "newest" | "oldest" | "available_quantity" | "stock_value"
  >("name");
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const { data: categories } = useInventoryCategories();
  const { data: locations } = useInventoryLocations();

  const { data, isLoading, isError, refetch } = useInventoryItemList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    categoryId: categoryId === ALL ? undefined : categoryId,
    locationId: locationId === ALL ? undefined : locationId,
    lowStock: lowStock || undefined,
    outOfStock: outOfStock || undefined,
    sort,
  });

  const canCreate = hasPermission(currentUser, "inventory.items.create");
  const categoryName = useMemo(
    () => new Map((categories ?? []).map((c) => [c.id, c.name])),
    [categories],
  );

  const columns = useMemo<ColumnDef<InventoryItemListItem, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Item",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <Link
              href={`/inventory/items/${row.original.id}`}
              className="font-medium hover:underline"
            >
              {row.original.name}
            </Link>
            <span className="text-muted-foreground text-xs">{row.original.item_code}</span>
          </div>
        ),
      },
      {
        id: "category",
        header: "Category",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{categoryName.get(row.original.category_id) ?? "—"}</span>
        ),
      },
      {
        id: "current_stock",
        header: "On hand",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatQuantity(row.original.current_stock)}</span>
        ),
      },
      {
        id: "reserved_stock",
        header: "Reserved",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">
            {formatQuantity(row.original.reserved_stock)}
          </span>
        ),
      },
      {
        id: "reorder_level",
        header: "Reorder level",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">
            {formatQuantity(row.original.reorder_level)}
          </span>
        ),
      },
      {
        id: "stock_status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.stock_status)}
            tone={STOCK_STATUS_TONES[row.original.stock_status]}
          />
        ),
      },
      {
        id: "flags",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-1">
            {row.original.requires_batch_tracking && <StatusBadge label="Batch" tone="info" />}
            {row.original.requires_expiry_tracking && <StatusBadge label="Expiry" tone="info" />}
            {row.original.is_perishable && <StatusBadge label="Perishable" tone="neutral" />}
            {!row.original.is_active && <StatusBadge label="Archived" tone="neutral" />}
          </div>
        ),
      },
    ],
    [categoryName],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const hasActiveFilters =
    !!search || categoryId !== ALL || locationId !== ALL || lowStock || outOfStock;

  function resetFilters() {
    setSearchInput("");
    setCategoryId(ALL);
    setLocationId(ALL);
    setLowStock(false);
    setOutOfStock(false);
    setPage(1);
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Inventory Items"
        description="Every stock-controlled ingredient and operational material — never a sellable menu product."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New item
            </Button>
          ) : null
        }
      />

      <FilterBar
        search={searchInput}
        onSearchChange={(value) => {
          setSearchInput(value);
          setPage(1);
        }}
        searchPlaceholder="Search name, code, or barcode…"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={
          <>
            <Select
              value={categoryId}
              onValueChange={(value) => {
                setCategoryId(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44" aria-label="Filter by category">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All categories</SelectItem>
                {(categories ?? []).map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
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

            <Select
              value={lowStock ? "low" : outOfStock ? "out" : ALL}
              onValueChange={(value) => {
                setLowStock(value === "low");
                setOutOfStock(value === "out");
                setPage(1);
              }}
            >
              <SelectTrigger className="w-40" aria-label="Filter by stock health">
                <SelectValue placeholder="Stock health" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All stock levels</SelectItem>
                <SelectItem value="low">Low / critical</SelectItem>
                <SelectItem value="out">Out of stock</SelectItem>
              </SelectContent>
            </Select>

            <Select value={sort} onValueChange={(value) => setSort(value as typeof sort)}>
              <SelectTrigger className="w-44" aria-label="Sort by">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        }
      />

      {isError ? (
        <ErrorState title="Could not load inventory items" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No items match these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters, or search for a different item."
              : "Create the first inventory item to get started."
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

      <InventoryItemCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
