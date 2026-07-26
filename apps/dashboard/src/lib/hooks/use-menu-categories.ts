"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { DataResponse, MenuCategory, PaginatedResponse } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export interface CategoryListParams {
  page: number;
  pageSize: number;
  search?: string;
  isActive?: boolean;
  includeArchived?: boolean;
  sort?: string;
}

export function useCategoryList(params: CategoryListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.search) query.set("search", params.search);
  if (params.isActive !== undefined) query.set("is_active", String(params.isActive));
  if (params.includeArchived) query.set("include_archived", "true");
  if (params.sort) query.set("sort", params.sort);

  return useQuery({
    queryKey: ["menu-categories", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<MenuCategory>>(
        `/api/v1/menu/categories?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useCategoryDetail(categoryId: string | undefined) {
  return useQuery({
    queryKey: ["menu-categories", categoryId],
    queryFn: () =>
      apiFetchClient<DataResponse<MenuCategory>>(`/api/v1/menu/categories/${categoryId}`),
    select: (response) => response.data,
    enabled: !!categoryId,
  });
}

function useInvalidateCategories(categoryId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["menu-categories"] });
    if (categoryId) queryClient.invalidateQueries({ queryKey: ["menu-categories", categoryId] });
  };
}

export interface CreateCategoryInput {
  code: string;
  name: string;
  description?: string | null;
  sort_order?: number;
  is_active?: boolean;
}

export function useCreateCategory() {
  const invalidate = useInvalidateCategories();
  return useMutation({
    mutationFn: (input: CreateCategoryInput) =>
      apiFetchClient<DataResponse<MenuCategory>>("/api/v1/menu/categories", {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateCategory(categoryId: string) {
  const invalidate = useInvalidateCategories(categoryId);
  return useMutation({
    mutationFn: (input: Record<string, unknown>) =>
      apiFetchClient<DataResponse<MenuCategory>>(`/api/v1/menu/categories/${categoryId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useArchiveCategory(categoryId: string) {
  const invalidate = useInvalidateCategories(categoryId);
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`/api/v1/menu/categories/${categoryId}`, {
        method: "DELETE",
        body: { reason },
      }),
    onSuccess: invalidate,
  });
}

export function useRestoreCategory(categoryId: string) {
  const invalidate = useInvalidateCategories(categoryId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<MenuCategory>>(`/api/v1/menu/categories/${categoryId}/restore`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useReorderCategories() {
  const invalidate = useInvalidateCategories();
  return useMutation({
    mutationFn: (orderedCategoryIds: string[]) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>("/api/v1/menu/categories/reorder", {
        method: "POST",
        body: { ordered_category_ids: orderedCategoryIds },
      }),
    onSuccess: invalidate,
  });
}
