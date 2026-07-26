"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  PaginatedResponse,
  Product,
  ProductImage,
  ProductListItem,
  ProductModifierGroupMapping,
  ProductVariant,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export interface ProductListParams {
  page: number;
  pageSize: number;
  search?: string;
  categoryId?: string;
  isActive?: boolean;
  includeArchived?: boolean;
  isVegetarian?: boolean;
  isVegan?: boolean;
  isFeatured?: boolean;
  isAvailable?: boolean;
  dineInAvailable?: boolean;
  takeawayAvailable?: boolean;
  deliveryAvailable?: boolean;
  taxCategory?: string;
  sort?: string;
}

export function useProductList(params: ProductListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.search) query.set("search", params.search);
  if (params.categoryId) query.set("category_id", params.categoryId);
  if (params.isActive !== undefined) query.set("is_active", String(params.isActive));
  if (params.includeArchived) query.set("include_archived", "true");
  if (params.isVegetarian !== undefined) query.set("is_vegetarian", String(params.isVegetarian));
  if (params.isVegan !== undefined) query.set("is_vegan", String(params.isVegan));
  if (params.isFeatured !== undefined) query.set("is_featured", String(params.isFeatured));
  if (params.isAvailable !== undefined) query.set("is_available", String(params.isAvailable));
  if (params.dineInAvailable !== undefined) {
    query.set("dine_in_available", String(params.dineInAvailable));
  }
  if (params.takeawayAvailable !== undefined) {
    query.set("takeaway_available", String(params.takeawayAvailable));
  }
  if (params.deliveryAvailable !== undefined) {
    query.set("delivery_available", String(params.deliveryAvailable));
  }
  if (params.taxCategory) query.set("tax_category", params.taxCategory);
  if (params.sort) query.set("sort", params.sort);

  return useQuery({
    queryKey: ["menu-products", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ProductListItem>>(`/api/v1/menu/products?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useProductDetail(productId: string | undefined) {
  return useQuery({
    queryKey: ["menu-products", productId],
    queryFn: () => apiFetchClient<DataResponse<Product>>(`/api/v1/menu/products/${productId}`),
    select: (response) => response.data,
    enabled: !!productId,
  });
}

function useInvalidateProducts(productId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["menu-products"] });
    if (productId) queryClient.invalidateQueries({ queryKey: ["menu-products", productId] });
  };
}

export interface CreateProductInput {
  category_id: string;
  name: string;
  display_name?: string | null;
  description?: string | null;
  short_description?: string | null;
  barcode?: string | null;
  food_type: string;
  is_jain_capable?: boolean;
  is_vegan_capable?: boolean;
  contains_egg?: boolean;
  contains_dairy?: boolean;
  contains_gluten?: boolean;
  contains_nuts?: boolean;
  contains_soy?: boolean;
  contains_alcohol?: boolean;
  spice_level?: string | null;
  preparation_minutes?: number | null;
  calories?: number | null;
  base_price_minor: number;
  tax_category?: string | null;
  dine_in_available?: boolean;
  takeaway_available?: boolean;
  delivery_available?: boolean;
  is_featured?: boolean;
  is_chef_recommended?: boolean;
}

export function useCreateProduct() {
  const invalidate = useInvalidateProducts();
  return useMutation({
    mutationFn: (input: CreateProductInput) =>
      apiFetchClient<DataResponse<Product>>("/api/v1/menu/products", {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateProduct(productId: string) {
  const invalidate = useInvalidateProducts(productId);
  return useMutation({
    mutationFn: (input: Record<string, unknown>) =>
      apiFetchClient<DataResponse<Product>>(`/api/v1/menu/products/${productId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useDuplicateProduct(productId: string) {
  const invalidate = useInvalidateProducts();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<Product>>(`/api/v1/menu/products/${productId}/duplicate`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useSetAvailabilityOverride(productId: string) {
  const invalidate = useInvalidateProducts(productId);
  return useMutation({
    mutationFn: (input: { isAvailable: boolean; reason: string }) =>
      apiFetchClient<DataResponse<Product>>(
        `/api/v1/menu/products/${productId}/availability-override`,
        { method: "POST", body: { is_available: input.isAvailable, reason: input.reason } },
      ),
    onSuccess: invalidate,
  });
}

export function useArchiveProduct(productId: string) {
  const invalidate = useInvalidateProducts(productId);
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`/api/v1/menu/products/${productId}`, {
        method: "DELETE",
        body: { reason },
      }),
    onSuccess: invalidate,
  });
}

export function useRestoreProduct(productId: string) {
  const invalidate = useInvalidateProducts(productId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<Product>>(`/api/v1/menu/products/${productId}/restore`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

// --- Variants ---------------------------------------------------------

export function useProductVariants(productId: string | undefined) {
  return useQuery({
    queryKey: ["menu-products", productId, "variants"],
    queryFn: () =>
      apiFetchClient<DataResponse<ProductVariant[]>>(`/api/v1/menu/products/${productId}/variants`),
    select: (response) => response.data,
    enabled: !!productId,
  });
}

export interface VariantInput {
  code: string;
  name: string;
  price_minor: number;
  sort_order?: number;
  is_active?: boolean;
  is_available?: boolean;
  preparation_minutes?: number | null;
}

function useInvalidateVariants(productId: string) {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["menu-products", productId, "variants"] });
}

export function useAddVariant(productId: string) {
  const invalidate = useInvalidateVariants(productId);
  return useMutation({
    mutationFn: (input: VariantInput) =>
      apiFetchClient<DataResponse<ProductVariant>>(`/api/v1/menu/products/${productId}/variants`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateVariant(productId: string) {
  const invalidate = useInvalidateVariants(productId);
  return useMutation({
    mutationFn: (input: { variantId: string } & VariantInput) =>
      apiFetchClient<DataResponse<ProductVariant>>(
        `/api/v1/menu/products/${productId}/variants/${input.variantId}`,
        { method: "PATCH", body: input },
      ),
    onSuccess: invalidate,
  });
}

export function useArchiveVariant(productId: string) {
  const invalidate = useInvalidateVariants(productId);
  return useMutation({
    mutationFn: (variantId: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `/api/v1/menu/products/${productId}/variants/${variantId}`,
        { method: "DELETE" },
      ),
    onSuccess: invalidate,
  });
}

// --- Images -----------------------------------------------------------

export function useProductImages(productId: string | undefined) {
  return useQuery({
    queryKey: ["menu-products", productId, "images"],
    queryFn: () =>
      apiFetchClient<DataResponse<ProductImage[]>>(`/api/v1/menu/products/${productId}/images`),
    select: (response) => response.data,
    enabled: !!productId,
  });
}

function useInvalidateImages(productId: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["menu-products", productId, "images"] });
    queryClient.invalidateQueries({ queryKey: ["menu-products", productId] });
  };
}

export function useUploadProductImage(productId: string) {
  const invalidate = useInvalidateImages(productId);
  return useMutation({
    mutationFn: (input: { file: File; altText?: string }) => {
      const formData = new FormData();
      formData.set("file", input.file);
      if (input.altText) formData.set("alt_text", input.altText);
      return apiFetchClient<DataResponse<ProductImage>>(
        `/api/v1/menu/products/${productId}/images`,
        { method: "POST", body: formData },
      );
    },
    onSuccess: invalidate,
  });
}

export function useDeleteProductImage(productId: string) {
  const invalidate = useInvalidateImages(productId);
  return useMutation({
    mutationFn: (imageId: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `/api/v1/menu/products/${productId}/images/${imageId}`,
        { method: "DELETE" },
      ),
    onSuccess: invalidate,
  });
}

export function useReorderProductImages(productId: string) {
  const invalidate = useInvalidateImages(productId);
  return useMutation({
    mutationFn: (orderedImageIds: string[]) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `/api/v1/menu/products/${productId}/images/reorder`,
        { method: "POST", body: { ordered_image_ids: orderedImageIds } },
      ),
    onSuccess: invalidate,
  });
}

export function useSetThumbnail(productId: string) {
  const invalidate = useInvalidateImages(productId);
  return useMutation({
    mutationFn: (imageId: string) =>
      apiFetchClient<DataResponse<ProductImage>>(
        `/api/v1/menu/products/${productId}/images/${imageId}/set-thumbnail`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

// --- Product modifier group mappings ---------------------------------

export function useProductModifierGroups(productId: string | undefined) {
  return useQuery({
    queryKey: ["menu-products", productId, "modifier-groups"],
    queryFn: () =>
      apiFetchClient<DataResponse<ProductModifierGroupMapping[]>>(
        `/api/v1/menu/products/${productId}/modifier-groups`,
      ),
    select: (response) => response.data,
    enabled: !!productId,
  });
}

function useInvalidateProductModifierGroups(productId: string) {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({ queryKey: ["menu-products", productId, "modifier-groups"] });
}

export function useAttachModifierGroup(productId: string) {
  const invalidate = useInvalidateProductModifierGroups(productId);
  return useMutation({
    mutationFn: (input: { modifierGroupId: string; sortOrder?: number }) =>
      apiFetchClient<DataResponse<ProductModifierGroupMapping>>(
        `/api/v1/menu/products/${productId}/modifier-groups`,
        {
          method: "POST",
          body: { modifier_group_id: input.modifierGroupId, sort_order: input.sortOrder ?? 0 },
        },
      ),
    onSuccess: invalidate,
  });
}

export function useDetachModifierGroup(productId: string) {
  const invalidate = useInvalidateProductModifierGroups(productId);
  return useMutation({
    mutationFn: (modifierGroupId: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `/api/v1/menu/products/${productId}/modifier-groups/${modifierGroupId}`,
        { method: "DELETE" },
      ),
    onSuccess: invalidate,
  });
}
