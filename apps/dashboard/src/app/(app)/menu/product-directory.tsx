"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { ProductListItem } from "@rkpr/contracts";
import { Copy, Plus } from "lucide-react";

import { useCategoryList } from "@/lib/hooks/use-menu-categories";
import { useDuplicateProduct, useProductList } from "@/lib/hooks/use-menu-products";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  FOOD_TYPE_TONES,
  PRODUCT_ACTIVE_TONE,
  PRODUCT_AVAILABILITY_TONE,
  formatMinorUnits,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { FilterBar } from "@/components/filter-bar";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ProductCreateModal } from "./product-create-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "display_order", label: "Display order" },
  { value: "alphabetical", label: "Alphabetical" },
  { value: "newest", label: "Newest" },
  { value: "oldest", label: "Oldest" },
  { value: "price", label: "Price" },
];

function DuplicateButton({ productId }: { productId: string }) {
  const duplicateProduct = useDuplicateProduct(productId);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        variant="ghost"
        size="icon"
        className="size-8"
        aria-label="Duplicate product"
        disabled={duplicateProduct.isPending}
        onClick={(e) => {
          e.stopPropagation();
          setError(null);
          duplicateProduct.mutate(undefined, {
            onError: (err) =>
              setError(err instanceof ApiError ? err.message : "Could not duplicate."),
          });
        }}
      >
        <Copy className="size-4" />
      </Button>
      {error && <span className="text-destructive text-xs">{error}</span>}
    </div>
  );
}

export function ProductDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [categoryId, setCategoryId] = useState(ALL);
  const [isActive, setIsActive] = useState(ALL);
  const [isVegetarian, setIsVegetarian] = useState(ALL);
  const [isFeatured, setIsFeatured] = useState(false);
  const [sort, setSort] = useState("display_order");
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const { data: categories } = useCategoryList({ page: 1, pageSize: 100, sort: "sort_order" });

  const { data, isLoading, isError, refetch } = useProductList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    categoryId: categoryId === ALL ? undefined : categoryId,
    isActive: isActive === ALL ? undefined : isActive === "true",
    isVegetarian: isVegetarian === ALL ? undefined : isVegetarian === "true",
    isFeatured: isFeatured || undefined,
    sort,
  });

  const canCreate = hasPermission(currentUser, "menu.create");

  const columns = useMemo<ColumnDef<ProductListItem, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Product",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <Link
              href={`/menu/products/${row.original.id}`}
              className="font-medium hover:underline"
            >
              {row.original.display_name ?? row.original.name}
            </Link>
            <span className="text-muted-foreground text-xs">{row.original.product_code}</span>
          </div>
        ),
      },
      {
        id: "food_type",
        header: "Food type",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.food_type)}
            tone={FOOD_TYPE_TONES[row.original.food_type]}
          />
        ),
      },
      {
        id: "base_price_minor",
        header: "Price",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatMinorUnits(row.original.base_price_minor)}</span>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-1">
            <StatusBadge
              label={row.original.is_active ? "Active" : "Inactive"}
              tone={PRODUCT_ACTIVE_TONE[row.original.is_active ? "active" : "inactive"]}
            />
            <StatusBadge
              label={row.original.is_available ? "Available" : "Unavailable"}
              tone={PRODUCT_AVAILABILITY_TONE[row.original.is_available ? "available" : "unavailable"]}
            />
            {row.original.is_featured && <StatusBadge label="Featured" tone="info" />}
          </div>
        ),
      },
      ...(canCreate
        ? [
            {
              id: "actions",
              header: "",
              enableSorting: false,
              cell: ({ row }: { row: { original: ProductListItem } }) => (
                <DuplicateButton productId={row.original.id} />
              ),
            } satisfies ColumnDef<ProductListItem, unknown>,
          ]
        : []),
    ],
    [canCreate],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const hasActiveFilters =
    !!search || categoryId !== ALL || isActive !== ALL || isVegetarian !== ALL || isFeatured;

  function resetFilters() {
    setSearchInput("");
    setCategoryId(ALL);
    setIsActive(ALL);
    setIsVegetarian(ALL);
    setIsFeatured(false);
    setPage(1);
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Menu Products"
        description="The full RKPR product catalog — pricing, variants, modifiers, images, and availability."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New product
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
        searchPlaceholder="Search name, SKU, or barcode…"
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
                {(categories?.data ?? []).map((category) => (
                  <SelectItem key={category.id} value={category.id}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={isActive}
              onValueChange={(value) => {
                setIsActive(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-36" aria-label="Filter by active state">
                <SelectValue placeholder="Active" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>Active + inactive</SelectItem>
                <SelectItem value="true">Active only</SelectItem>
                <SelectItem value="false">Inactive only</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={isVegetarian}
              onValueChange={(value) => {
                setIsVegetarian(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-36" aria-label="Filter by food type">
                <SelectValue placeholder="Food type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All food types</SelectItem>
                <SelectItem value="true">Vegetarian</SelectItem>
                <SelectItem value="false">Non-vegetarian</SelectItem>
              </SelectContent>
            </Select>

            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={isFeatured}
                onCheckedChange={(checked) => {
                  setIsFeatured(checked === true);
                  setPage(1);
                }}
              />
              Featured only
            </label>

            <Select value={sort} onValueChange={setSort}>
              <SelectTrigger className="w-40" aria-label="Sort by">
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
        <ErrorState
          title="Could not load products"
          onRetry={() => void refetch()}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No products match these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters, or search for a different item."
              : "Create the first product to get started."
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

      <ProductCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
