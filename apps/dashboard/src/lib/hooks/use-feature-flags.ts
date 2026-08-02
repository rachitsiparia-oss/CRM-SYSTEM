"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { DataResponse, FeatureFlag, FeatureFlagCreateInput } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/feature-flags";

export function useFeatureFlagList() {
  return useQuery({
    queryKey: ["feature-flags", "list"],
    queryFn: () => apiFetchClient<DataResponse<FeatureFlag[]>>(BASE),
    select: (response) => response.data,
  });
}

export function useCreateFeatureFlag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: FeatureFlagCreateInput) =>
      apiFetchClient<DataResponse<FeatureFlag>>(BASE, { method: "POST", body: input }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["feature-flags"] }),
  });
}

export function useSetFeatureFlagEnabled() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ flagId, isEnabled }: { flagId: string; isEnabled: boolean }) =>
      apiFetchClient<DataResponse<FeatureFlag>>(`${BASE}/${flagId}/enabled`, {
        method: "PATCH",
        body: { is_enabled: isEnabled },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["feature-flags"] }),
  });
}
