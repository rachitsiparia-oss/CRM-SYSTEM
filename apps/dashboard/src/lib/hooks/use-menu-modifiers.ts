"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { DataResponse, Modifier, ModifierGroup, ModifierGroupItem } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export function useModifierGroupList(includeArchived = false) {
  return useQuery({
    queryKey: ["modifier-groups", "list", includeArchived],
    queryFn: () =>
      apiFetchClient<DataResponse<ModifierGroup[]>>(
        `/api/v1/menu/modifier-groups?include_archived=${includeArchived}`,
      ),
    select: (response) => response.data,
  });
}

function useInvalidateModifierGroups(groupId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["modifier-groups"] });
    if (groupId) queryClient.invalidateQueries({ queryKey: ["modifier-groups", groupId] });
  };
}

export interface ModifierGroupInput {
  name: string;
  min_select: number;
  max_select: number;
  is_required: boolean;
  sort_order: number;
}

export function useCreateModifierGroup() {
  const invalidate = useInvalidateModifierGroups();
  return useMutation({
    mutationFn: (input: ModifierGroupInput) =>
      apiFetchClient<DataResponse<ModifierGroup>>("/api/v1/menu/modifier-groups", {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateModifierGroup(groupId: string) {
  const invalidate = useInvalidateModifierGroups(groupId);
  return useMutation({
    mutationFn: (input: ModifierGroupInput) =>
      apiFetchClient<DataResponse<ModifierGroup>>(`/api/v1/menu/modifier-groups/${groupId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useArchiveModifierGroup(groupId: string) {
  const invalidate = useInvalidateModifierGroups(groupId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`/api/v1/menu/modifier-groups/${groupId}`, {
        method: "DELETE",
      }),
    onSuccess: invalidate,
  });
}

export function useRestoreModifierGroup(groupId: string) {
  const invalidate = useInvalidateModifierGroups(groupId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `/api/v1/menu/modifier-groups/${groupId}/restore`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

export function useModifierGroupItems(groupId: string | undefined) {
  return useQuery({
    queryKey: ["modifier-groups", groupId, "items"],
    queryFn: () =>
      apiFetchClient<DataResponse<ModifierGroupItem[]>>(
        `/api/v1/menu/modifier-groups/${groupId}/items`,
      ),
    select: (response) => response.data,
    enabled: !!groupId,
  });
}

export function useAddModifierToGroup(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      modifierId: string;
      priceMinorOverride?: number | null;
      sortOrder?: number;
    }) =>
      apiFetchClient<DataResponse<ModifierGroupItem>>(
        `/api/v1/menu/modifier-groups/${groupId}/items`,
        {
          method: "POST",
          body: {
            modifier_id: input.modifierId,
            price_minor_override: input.priceMinorOverride ?? null,
            sort_order: input.sortOrder ?? 0,
          },
        },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["modifier-groups", groupId, "items"] }),
  });
}

export function useRemoveModifierFromGroup(groupId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (modifierId: string) =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(
        `/api/v1/menu/modifier-groups/${groupId}/items/${modifierId}`,
        { method: "DELETE" },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["modifier-groups", groupId, "items"] }),
  });
}

export function useModifierList(includeArchived = false) {
  return useQuery({
    queryKey: ["modifiers", "list", includeArchived],
    queryFn: () =>
      apiFetchClient<DataResponse<Modifier[]>>(
        `/api/v1/menu/modifiers?include_archived=${includeArchived}`,
      ),
    select: (response) => response.data,
  });
}

function useInvalidateModifiers() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["modifiers"] });
}

export interface ModifierInput {
  name: string;
  default_price_minor: number;
  is_active: boolean;
}

export function useCreateModifier() {
  const invalidate = useInvalidateModifiers();
  return useMutation({
    mutationFn: (input: ModifierInput) =>
      apiFetchClient<DataResponse<Modifier>>("/api/v1/menu/modifiers", {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateModifier(modifierId: string) {
  const invalidate = useInvalidateModifiers();
  return useMutation({
    mutationFn: (input: ModifierInput) =>
      apiFetchClient<DataResponse<Modifier>>(`/api/v1/menu/modifiers/${modifierId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useArchiveModifier(modifierId: string) {
  const invalidate = useInvalidateModifiers();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`/api/v1/menu/modifiers/${modifierId}`, {
        method: "DELETE",
      }),
    onSuccess: invalidate,
  });
}

export function useRestoreModifier(modifierId: string) {
  const invalidate = useInvalidateModifiers();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ ok: boolean }>>(`/api/v1/menu/modifiers/${modifierId}/restore`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}
