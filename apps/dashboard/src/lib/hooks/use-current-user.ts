"use client";

import { useQuery } from "@tanstack/react-query";
import type { CurrentUser, DataResponse } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";
import { ApiError } from "@/lib/api/errors";

export const currentUserQueryKey = ["auth", "me"] as const;

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: () => apiFetchClient<DataResponse<CurrentUser>>("/api/v1/auth/me"),
    select: (response) => response.data,
    staleTime: 60_000,
    // 401/403 are the backend's real answer ("not signed in" / "identity
    // not provisioned") — retrying can't change that. Everything else (a
    // network blip, a cold connection, a transient 5xx) is worth a couple
    // of retries before giving up: this hook backs every PermissionGate in
    // the app, so a single failed first request used to permanently show
    // "you don't have access" — indistinguishable from a real denial —
    // for the rest of that page load.
    retry: (failureCount, error) => {
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        return false;
      }
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 4000),
  });
}

export function hasPermission(user: CurrentUser | undefined, code: string): boolean {
  return user?.permissions.includes(code) ?? false;
}
