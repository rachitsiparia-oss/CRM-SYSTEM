"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { RecipeListItem } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useInventoryRecipes } from "@/lib/hooks/use-inventory-recipes";
import { useProductList } from "@/lib/hooks/use-menu-products";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatQuantity } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { RecipeCreateModal } from "./recipe-create-modal";

const PAGE_SIZE = 25;

export function RecipeDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);

  const { data: products } = useProductList({ page: 1, pageSize: 200, sort: "alphabetical" });
  const { data, isLoading, isError, refetch } = useInventoryRecipes({ page, pageSize: PAGE_SIZE });

  const canManage = hasPermission(currentUser, "inventory.recipes.manage");
  const productName = useMemo(
    () => new Map((products?.data ?? []).map((p) => [p.id, p.display_name ?? p.name])),
    [products],
  );

  const columns = useMemo<ColumnDef<RecipeListItem, unknown>[]>(
    () => [
      {
        id: "recipe_code",
        header: "Recipe",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <Link
              href={`/inventory/recipes/${row.original.id}`}
              className="font-medium hover:underline"
            >
              {productName.get(row.original.product_id) ?? "—"}
            </Link>
            <span className="text-muted-foreground text-xs">{row.original.recipe_code}</span>
          </div>
        ),
      },
      {
        id: "variant",
        header: "Scope",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{row.original.variant_id ? "Variant-specific" : "Base recipe"}</span>
        ),
      },
      {
        id: "yield",
        header: "Yield",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatQuantity(row.original.yield_quantity)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={row.original.is_active ? "Active" : "Archived"}
            tone={row.original.is_active ? "success" : "neutral"}
          />
        ),
      },
    ],
    [productName],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Recipes"
        description="Ingredient composition and yield for every recipe-tracked menu product and variant."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New recipe
            </Button>
          ) : null
        }
      />

      {isError ? (
        <ErrorState title="Could not load recipes" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No recipes yet"
          emptyDescription="Create a recipe to connect a menu product to its ingredients."
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: data?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      )}

      <RecipeCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
