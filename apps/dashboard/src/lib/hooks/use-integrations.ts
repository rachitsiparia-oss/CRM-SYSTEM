"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { DataResponse, HealthCheckSummary, Integration } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/integrations";

export function useIntegrationList(params?: { category?: string; healthState?: string }) {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.healthState) query.set("health_state", params.healthState);
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return useQuery({
    queryKey: ["integrations", "list", params],
    queryFn: () => apiFetchClient<DataResponse<Integration[]>>(`${BASE}${suffix}`),
    select: (response) => response.data,
  });
}

function useIntegrationLifecycleAction(action: "pause" | "resume" | "disable") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (integrationId: string) =>
      apiFetchClient<DataResponse<Integration>>(`${BASE}/${integrationId}/${action}`, {
        method: "POST",
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["integrations"] }),
  });
}

export function usePauseIntegration() {
  return useIntegrationLifecycleAction("pause");
}

export function useResumeIntegration() {
  return useIntegrationLifecycleAction("resume");
}

export function useDisableIntegration() {
  return useIntegrationLifecycleAction("disable");
}

export function useRunIntegrationHealthChecks() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<HealthCheckSummary>>(`${BASE}/run-health-checks`, {
        method: "POST",
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["integrations"] }),
  });
}
