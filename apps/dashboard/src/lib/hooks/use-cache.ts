"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { CacheFamily, DataResponse } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/cache";

export function useCacheFamilyList() {
  return useQuery({
    queryKey: ["cache", "families"],
    queryFn: () => apiFetchClient<DataResponse<CacheFamily[]>>(`${BASE}/families`),
    select: (response) => response.data,
  });
}

export function useInvalidateCacheFamily() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (family: string) =>
      apiFetchClient<DataResponse<{ keys_removed: number }>>(`${BASE}/invalidate`, {
        method: "POST",
        body: { family },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["cache"] }),
  });
}
