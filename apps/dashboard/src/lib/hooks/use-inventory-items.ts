"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  BalanceDrift,
  BalanceRebuildResult,
  DataResponse,
  InventoryBatch,
  InventoryDashboardStats,
  InventoryItem,
  InventoryItemCreateInput,
  InventoryItemListItem,
  InventoryItemUpdateInput,
  PaginatedResponse,
  StockBalance,
  StockMovement,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export interface InventoryItemListParams {
  page: number;
  pageSize: number;
  search?: string;
  categoryId?: string;
  locationId?: string;
  supplierId?: string;
  isActive?: boolean;
  includeArchived?: boolean;
  lowStock?: boolean;
  outOfStock?: boolean;
  perishable?: boolean;
  batchTracked?: boolean;
  expiryTracked?: boolean;
  sort?: "name" | "newest" | "oldest" | "available_quantity" | "stock_value";
}

export function useInventoryDashboardStats() {
  return useQuery({
    queryKey: ["inventory", "dashboard-stats"],
    queryFn: () =>
      apiFetchClient<DataResponse<InventoryDashboardStats>>("/api/v1/inventory/dashboard/stats"),
    select: (response) => response.data,
    refetchInterval: 60_000,
  });
}

export function useInventoryItemList(params: InventoryItemListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.search) query.set("search", params.search);
  if (params.categoryId) query.set("category_id", params.categoryId);
  if (params.locationId) query.set("location_id", params.locationId);
  if (params.supplierId) query.set("supplier_id", params.supplierId);
  if (params.isActive !== undefined) query.set("is_active", String(params.isActive));
  if (params.includeArchived) query.set("include_archived", "true");
  if (params.lowStock) query.set("low_stock", "true");
  if (params.outOfStock) query.set("out_of_stock", "true");
  if (params.perishable !== undefined) query.set("perishable", String(params.perishable));
  if (params.batchTracked !== undefined) query.set("batch_tracked", String(params.batchTracked));
  if (params.expiryTracked !== undefined)
    query.set("expiry_tracked", String(params.expiryTracked));
  if (params.sort) query.set("sort", params.sort);

  return useQuery({
    queryKey: ["inventory", "items", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<InventoryItemListItem>>(
        `/api/v1/inventory/items?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useInventoryItem(itemId: string | undefined) {
  return useQuery({
    queryKey: ["inventory", "items", itemId],
    queryFn: () => apiFetchClient<DataResponse<InventoryItem>>(`/api/v1/inventory/items/${itemId}`),
    select: (response) => response.data,
    enabled: !!itemId,
  });
}

export function useInventoryItemBalances(itemId: string | undefined) {
  return useQuery({
    queryKey: ["inventory", "items", itemId, "balances"],
    queryFn: () =>
      apiFetchClient<DataResponse<StockBalance[]>>(`/api/v1/inventory/items/${itemId}/balances`),
    select: (response) => response.data,
    enabled: !!itemId,
  });
}

export function useInventoryItemBatches(itemId: string | undefined, includeDepleted = false) {
  return useQuery({
    queryKey: ["inventory", "items", itemId, "batches", includeDepleted],
    queryFn: () =>
      apiFetchClient<DataResponse<InventoryBatch[]>>(
        `/api/v1/inventory/items/${itemId}/batches?include_depleted=${includeDepleted}`,
      ),
    select: (response) => response.data,
    enabled: !!itemId,
  });
}

export function useInventoryItemMovements(
  itemId: string | undefined,
  page: number,
  pageSize: number,
) {
  return useQuery({
    queryKey: ["inventory", "items", itemId, "movements", page, pageSize],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<StockMovement>>(
        `/api/v1/inventory/items/${itemId}/movements?page=${page}&page_size=${pageSize}`,
      ),
    enabled: !!itemId,
    placeholderData: (previous) => previous,
  });
}

function useInvalidateItems(itemId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["inventory", "items"] });
    queryClient.invalidateQueries({ queryKey: ["inventory", "dashboard-stats"] });
    if (itemId) queryClient.invalidateQueries({ queryKey: ["inventory", "items", itemId] });
  };
}

export function useCreateInventoryItem() {
  const invalidate = useInvalidateItems();
  return useMutation({
    mutationFn: (input: InventoryItemCreateInput) =>
      apiFetchClient<DataResponse<InventoryItem>>("/api/v1/inventory/items", {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateInventoryItem(itemId: string) {
  const invalidate = useInvalidateItems(itemId);
  return useMutation({
    mutationFn: (input: InventoryItemUpdateInput) =>
      apiFetchClient<DataResponse<InventoryItem>>(`/api/v1/inventory/items/${itemId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useArchiveInventoryItem(itemId: string) {
  const invalidate = useInvalidateItems(itemId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`/api/v1/inventory/items/${itemId}`, {
        method: "DELETE",
      }),
    onSuccess: invalidate,
  });
}

export function useRestoreInventoryItem(itemId: string) {
  const invalidate = useInvalidateItems(itemId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<InventoryItem>>(`/api/v1/inventory/items/${itemId}/restore`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

// --- Global movement ledger ---

export interface MovementListParams {
  page: number;
  pageSize: number;
  movementType?: string;
  inventoryItemId?: string;
  storageLocationId?: string;
  referenceType?: string;
  referenceId?: string;
  performedBy?: string;
  dateFrom?: string;
  dateTo?: string;
}

export function useInventoryMovements(params: MovementListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.movementType) query.set("movement_type", params.movementType);
  if (params.inventoryItemId) query.set("inventory_item_id", params.inventoryItemId);
  if (params.storageLocationId) query.set("storage_location_id", params.storageLocationId);
  if (params.referenceType) query.set("reference_type", params.referenceType);
  if (params.referenceId) query.set("reference_id", params.referenceId);
  if (params.performedBy) query.set("performed_by", params.performedBy);
  if (params.dateFrom) query.set("date_from", params.dateFrom);
  if (params.dateTo) query.set("date_to", params.dateTo);

  return useQuery({
    queryKey: ["inventory", "movements", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<StockMovement>>(
        `/api/v1/inventory/movements?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

// --- Balance verification and rebuild ---

export function useVerifyInventoryBalances(itemId?: string) {
  const query = itemId ? `?inventory_item_id=${itemId}` : "";
  return useQuery({
    queryKey: ["inventory", "balances", "verify", itemId],
    queryFn: () =>
      apiFetchClient<DataResponse<BalanceDrift[]>>(`/api/v1/inventory/balances/verify${query}`),
    select: (response) => response.data,
    enabled: false, // run on demand — this is a diagnostic action, not a page load
  });
}

export function useRebuildInventoryBalances() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (itemId?: string) => {
      const query = itemId ? `?inventory_item_id=${itemId}` : "";
      return apiFetchClient<DataResponse<BalanceRebuildResult>>(
        `/api/v1/inventory/balances/rebuild${query}`,
        { method: "POST" },
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory"] });
    },
  });
}
