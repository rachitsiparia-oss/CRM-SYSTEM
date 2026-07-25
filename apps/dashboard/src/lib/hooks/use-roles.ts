"use client";

import { useQuery } from "@tanstack/react-query";
import type { DataResponse, Permission, RoleListItem, RolePermissions } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export function useRoles() {
  return useQuery({
    queryKey: ["roles"],
    queryFn: () => apiFetchClient<DataResponse<RoleListItem[]>>("/api/v1/roles"),
    select: (response) => response.data,
    staleTime: 5 * 60_000,
  });
}

export function useRolePermissions(roleId: string | undefined) {
  return useQuery({
    queryKey: ["roles", roleId, "permissions"],
    queryFn: () =>
      apiFetchClient<DataResponse<RolePermissions>>(`/api/v1/roles/${roleId}/permissions`),
    select: (response) => response.data,
    enabled: !!roleId,
  });
}

export function usePermissions() {
  return useQuery({
    queryKey: ["permissions"],
    queryFn: () => apiFetchClient<DataResponse<Permission[]>>("/api/v1/permissions"),
    select: (response) => response.data,
    staleTime: 5 * 60_000,
  });
}
