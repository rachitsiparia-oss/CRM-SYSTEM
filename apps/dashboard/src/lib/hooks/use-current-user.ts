"use client";

import { useQuery } from "@tanstack/react-query";
import type { CurrentUser, DataResponse } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export const currentUserQueryKey = ["auth", "me"] as const;

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: () => apiFetchClient<DataResponse<CurrentUser>>("/api/v1/auth/me"),
    select: (response) => response.data,
    staleTime: 60_000,
    retry: false,
  });
}

export function hasPermission(user: CurrentUser | undefined, code: string): boolean {
  return user?.permissions.includes(code) ?? false;
}
