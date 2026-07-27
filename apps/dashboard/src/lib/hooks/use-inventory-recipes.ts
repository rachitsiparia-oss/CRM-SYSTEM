"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  PaginatedResponse,
  Recipe,
  RecipeCost,
  RecipeCreateInput,
  RecipeItem,
  RecipeItemCreateInput,
  RecipeListItem,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export interface RecipeListParams {
  page: number;
  pageSize: number;
  productId?: string;
  isActive?: boolean;
}

export function useInventoryRecipes(params: RecipeListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.productId) query.set("product_id", params.productId);
  if (params.isActive !== undefined) query.set("is_active", String(params.isActive));

  return useQuery({
    queryKey: ["inventory", "recipes", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<RecipeListItem>>(
        `/api/v1/inventory/recipes?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useInventoryRecipe(recipeId: string | undefined) {
  return useQuery({
    queryKey: ["inventory", "recipes", recipeId],
    queryFn: () => apiFetchClient<DataResponse<Recipe>>(`/api/v1/inventory/recipes/${recipeId}`),
    select: (response) => response.data,
    enabled: !!recipeId,
  });
}

export function useInventoryRecipeCost(recipeId: string | undefined) {
  return useQuery({
    queryKey: ["inventory", "recipes", recipeId, "cost"],
    queryFn: () =>
      apiFetchClient<DataResponse<RecipeCost>>(`/api/v1/inventory/recipes/${recipeId}/cost`),
    select: (response) => response.data,
    enabled: !!recipeId,
  });
}

export function useResolveRecipe(productId: string | undefined, variantId?: string) {
  const query = new URLSearchParams();
  if (productId) query.set("product_id", productId);
  if (variantId) query.set("variant_id", variantId);
  return useQuery({
    queryKey: ["inventory", "recipes", "resolve", productId, variantId],
    queryFn: () =>
      apiFetchClient<DataResponse<Recipe | null>>(
        `/api/v1/inventory/recipes/resolve?${query.toString()}`,
      ),
    select: (response) => response.data,
    enabled: !!productId,
  });
}

function useInvalidateRecipes(recipeId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["inventory", "recipes"] });
    if (recipeId) queryClient.invalidateQueries({ queryKey: ["inventory", "recipes", recipeId] });
  };
}

export function useCreateInventoryRecipe() {
  const invalidate = useInvalidateRecipes();
  return useMutation({
    mutationFn: (input: RecipeCreateInput) =>
      apiFetchClient<DataResponse<Recipe>>("/api/v1/inventory/recipes", {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAddRecipeItem(recipeId: string) {
  const invalidate = useInvalidateRecipes(recipeId);
  return useMutation({
    mutationFn: (input: RecipeItemCreateInput) =>
      apiFetchClient<DataResponse<RecipeItem>>(`/api/v1/inventory/recipes/${recipeId}/items`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useArchiveInventoryRecipe(recipeId: string) {
  const invalidate = useInvalidateRecipes(recipeId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`/api/v1/inventory/recipes/${recipeId}`, {
        method: "DELETE",
      }),
    onSuccess: invalidate,
  });
}
