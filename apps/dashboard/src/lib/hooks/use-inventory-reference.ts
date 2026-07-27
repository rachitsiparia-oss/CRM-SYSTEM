"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  InventoryCategory,
  InventoryCategoryCreateInput,
  PaginatedResponse,
  StorageLocation,
  StorageLocationCreateInput,
  Supplier,
  SupplierCreateInput,
  SupplierUpdateInput,
  UnitOfMeasure,
  UnitCreateInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

// Reference data (units of measure, categories, storage locations,
// suppliers) — small, rarely-changing lists, so no pagination and a long
// staleTime; callers reuse this data across every other inventory page
// rather than each page re-fetching it.
const REFERENCE_STALE_TIME_MS = 60_000;

export function useInventoryUnits() {
  return useQuery({
    queryKey: ["inventory", "units"],
    queryFn: () => apiFetchClient<DataResponse<UnitOfMeasure[]>>("/api/v1/inventory/units"),
    select: (response) => response.data,
    staleTime: REFERENCE_STALE_TIME_MS,
  });
}

export function useCreateInventoryUnit() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UnitCreateInput) =>
      apiFetchClient<DataResponse<UnitOfMeasure>>("/api/v1/inventory/units", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inventory", "units"] }),
  });
}

export function useInventoryCategories(includeArchived = false) {
  return useQuery({
    queryKey: ["inventory", "categories", includeArchived],
    queryFn: () =>
      apiFetchClient<DataResponse<InventoryCategory[]>>(
        `/api/v1/inventory/categories?include_archived=${includeArchived}`,
      ),
    select: (response) => response.data,
    staleTime: REFERENCE_STALE_TIME_MS,
  });
}

export function useCreateInventoryCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: InventoryCategoryCreateInput) =>
      apiFetchClient<DataResponse<InventoryCategory>>("/api/v1/inventory/categories", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inventory", "categories"] }),
  });
}

export function useInventoryLocations(includeArchived = false) {
  return useQuery({
    queryKey: ["inventory", "locations", includeArchived],
    queryFn: () =>
      apiFetchClient<DataResponse<StorageLocation[]>>(
        `/api/v1/inventory/locations?include_archived=${includeArchived}`,
      ),
    select: (response) => response.data,
    staleTime: REFERENCE_STALE_TIME_MS,
  });
}

export function useCreateInventoryLocation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: StorageLocationCreateInput) =>
      apiFetchClient<DataResponse<StorageLocation>>("/api/v1/inventory/locations", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inventory", "locations"] }),
  });
}

export interface InventorySupplierListParams {
  page?: number;
  pageSize?: number;
  search?: string;
}

export function useInventorySuppliers(params: InventorySupplierListParams = {}) {
  const page = params.page ?? 1;
  const pageSize = params.pageSize ?? 100;
  const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (params.search) query.set("search", params.search);

  return useQuery({
    queryKey: ["inventory", "suppliers", "list", page, pageSize, params.search],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<Supplier>>(`/api/v1/inventory/suppliers?${query.toString()}`),
    staleTime: REFERENCE_STALE_TIME_MS,
    placeholderData: (previous) => previous,
  });
}

export function useInventorySupplier(supplierId: string | undefined) {
  return useQuery({
    queryKey: ["inventory", "suppliers", supplierId],
    queryFn: () => apiFetchClient<DataResponse<Supplier>>(`/api/v1/inventory/suppliers/${supplierId}`),
    select: (response) => response.data,
    enabled: !!supplierId,
  });
}

export function useCreateInventorySupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SupplierCreateInput) =>
      apiFetchClient<DataResponse<Supplier>>("/api/v1/inventory/suppliers", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inventory", "suppliers"] }),
  });
}

export function useUpdateInventorySupplier(supplierId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SupplierUpdateInput) =>
      apiFetchClient<DataResponse<Supplier>>(`/api/v1/inventory/suppliers/${supplierId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["inventory", "suppliers"] });
    },
  });
}

export function useArchiveInventorySupplier(supplierId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<Supplier>>(`/api/v1/inventory/suppliers/${supplierId}`, {
        method: "DELETE",
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inventory", "suppliers"] }),
  });
}

export function useRestoreInventorySupplier(supplierId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<Supplier>>(`/api/v1/inventory/suppliers/${supplierId}/restore`, {
        method: "POST",
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["inventory", "suppliers"] }),
  });
}
