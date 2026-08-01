"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  ForecastDefinition,
  ForecastDefinitionCreateInput,
  ForecastSnapshot,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/forecasts";

export function useForecastDefinitionList(isActive?: boolean) {
  const query = new URLSearchParams();
  if (isActive !== undefined) query.set("is_active", String(isActive));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return useQuery({
    queryKey: ["forecasts", "definitions", isActive],
    queryFn: () =>
      apiFetchClient<DataResponse<ForecastDefinition[]>>(`${BASE}/definitions${suffix}`),
    select: (response) => response.data,
  });
}

export function useCreateForecastDefinition() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ForecastDefinitionCreateInput) =>
      apiFetchClient<DataResponse<ForecastDefinition>>(`${BASE}/definitions`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["forecasts", "definitions"] }),
  });
}

export function useRunForecast(definitionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<ForecastSnapshot>>(
        `${BASE}/definitions/${definitionId}/run`,
        { method: "POST" },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["forecasts", "definitions", definitionId, "snapshots"],
      }),
  });
}

export function useForecastSnapshotList(
  definitionId: string | undefined,
  page: number,
  pageSize: number,
) {
  return useQuery({
    queryKey: ["forecasts", "definitions", definitionId, "snapshots", page, pageSize],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ForecastSnapshot>>(
        `${BASE}/definitions/${definitionId}/snapshots?page=${page}&page_size=${pageSize}`,
      ),
    enabled: !!definitionId,
    placeholderData: (previous) => previous,
  });
}
