"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  AnomalyFinding,
  AnomalyFindingTransitionInput,
  AnomalyRule,
  AnomalyRuleCreateInput,
  AnomalyRuleUpdateInput,
  DataResponse,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/anomalies";

export function useAnomalyRuleList(isActive?: boolean) {
  const query = new URLSearchParams();
  if (isActive !== undefined) query.set("is_active", String(isActive));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return useQuery({
    queryKey: ["anomalies", "rules", isActive],
    queryFn: () => apiFetchClient<DataResponse<AnomalyRule[]>>(`${BASE}/rules${suffix}`),
    select: (response) => response.data,
  });
}

function useInvalidateAnomalyRules() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["anomalies", "rules"] });
}

export function useCreateAnomalyRule() {
  const invalidate = useInvalidateAnomalyRules();
  return useMutation({
    mutationFn: (input: AnomalyRuleCreateInput) =>
      apiFetchClient<DataResponse<AnomalyRule>>(`${BASE}/rules`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateAnomalyRule(ruleId: string) {
  const invalidate = useInvalidateAnomalyRules();
  return useMutation({
    mutationFn: (input: AnomalyRuleUpdateInput) =>
      apiFetchClient<DataResponse<AnomalyRule>>(`${BASE}/rules/${ruleId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useEvaluateAnomalyRules() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<AnomalyFinding[]>>(`${BASE}/evaluate`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["anomalies", "findings"] }),
  });
}

export interface AnomalyFindingListParams {
  page: number;
  pageSize: number;
  status?: string;
  severity?: string;
}

export function useAnomalyFindingList(params: AnomalyFindingListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.severity) query.set("severity", params.severity);
  return useQuery({
    queryKey: ["anomalies", "findings", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<AnomalyFinding>>(`${BASE}/findings?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useAnomalyFindingDetail(findingId: string | undefined) {
  return useQuery({
    queryKey: ["anomalies", "findings", findingId],
    queryFn: () =>
      apiFetchClient<DataResponse<AnomalyFinding>>(`${BASE}/findings/${findingId}`),
    select: (response) => response.data,
    enabled: !!findingId,
  });
}

export function useTransitionAnomalyFinding(findingId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AnomalyFindingTransitionInput) =>
      apiFetchClient<DataResponse<AnomalyFinding>>(`${BASE}/findings/${findingId}/transition`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["anomalies", "findings"] });
    },
  });
}
