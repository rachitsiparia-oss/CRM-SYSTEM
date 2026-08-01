"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DashboardResult,
  DataResponse,
  DrilldownResult,
  MetricDef,
  PaginatedResponse,
  ReportDefinition,
  ReportDefinitionCreateInput,
  ReportDefinitionShare,
  ReportDefinitionShareInput,
  ReportDefinitionUpdateInput,
  ReportRunDetail,
  ReportRunRequestInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export function useMetricCatalog() {
  return useQuery({
    queryKey: ["analytics", "metrics"],
    queryFn: () => apiFetchClient<DataResponse<MetricDef[]>>("/api/v1/analytics/metrics"),
    select: (response) => response.data,
  });
}

export function useDashboard(
  domain: string,
  windowCode: string,
  customRange?: { start: string; end: string },
) {
  const query = new URLSearchParams({ window: windowCode });
  if (windowCode === "custom" && customRange) {
    query.set("custom_start", customRange.start);
    query.set("custom_end", customRange.end);
  }
  return useQuery({
    queryKey: ["dashboard", domain, windowCode, customRange],
    queryFn: () =>
      apiFetchClient<DataResponse<DashboardResult>>(
        `/api/v1/dashboard/${domain}?${query.toString()}`,
      ),
    select: (response) => response.data,
    enabled: !!domain && (windowCode !== "custom" || !!customRange),
  });
}

export function useDrilldown(metricCode: string | undefined, windowCode: string) {
  return useQuery({
    queryKey: ["reports", "drilldown", metricCode, windowCode],
    queryFn: () =>
      apiFetchClient<DataResponse<DrilldownResult>>(
        `/api/v1/reports/drilldown?metric_code=${metricCode}&window=${windowCode}`,
      ),
    select: (response) => response.data,
    enabled: !!metricCode,
  });
}

export interface ReportDefinitionListParams {
  page: number;
  pageSize: number;
  domain?: string;
}

export function useReportDefinitionList(params: ReportDefinitionListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.domain) query.set("domain", params.domain);
  return useQuery({
    queryKey: ["reports", "definitions", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ReportDefinition>>(
        `/api/v1/reports/definitions?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useReportDefinitionDetail(definitionId: string | undefined) {
  return useQuery({
    queryKey: ["reports", "definitions", definitionId],
    queryFn: () =>
      apiFetchClient<DataResponse<ReportDefinition>>(
        `/api/v1/reports/definitions/${definitionId}`,
      ),
    select: (response) => response.data,
    enabled: !!definitionId,
  });
}

function useInvalidateReportDefinitions() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["reports", "definitions"] });
}

export function useCreateReportDefinition() {
  const invalidate = useInvalidateReportDefinitions();
  return useMutation({
    mutationFn: (input: ReportDefinitionCreateInput) =>
      apiFetchClient<DataResponse<ReportDefinition>>("/api/v1/reports/definitions", {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateReportDefinition(definitionId: string) {
  const invalidate = useInvalidateReportDefinitions();
  return useMutation({
    mutationFn: (input: ReportDefinitionUpdateInput) =>
      apiFetchClient<DataResponse<ReportDefinition>>(
        `/api/v1/reports/definitions/${definitionId}`,
        { method: "PATCH", body: input },
      ),
    onSuccess: invalidate,
  });
}

export function useShareReportDefinition(definitionId: string) {
  return useMutation({
    mutationFn: (input: ReportDefinitionShareInput) =>
      apiFetchClient<DataResponse<ReportDefinitionShare>>(
        `/api/v1/reports/definitions/${definitionId}/share`,
        { method: "POST", body: input },
      ),
  });
}

export function useRunReportDefinition(definitionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ReportRunRequestInput) =>
      apiFetchClient<DataResponse<ReportRunDetail>>(
        `/api/v1/reports/definitions/${definitionId}/run`,
        { method: "POST", body: input },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports", "runs"] });
    },
  });
}

export interface ReportRunListParams {
  page: number;
  pageSize: number;
  reportDefinitionId?: string;
}

export function useReportRunList(params: ReportRunListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.reportDefinitionId) query.set("report_definition_id", params.reportDefinitionId);
  return useQuery({
    queryKey: ["reports", "runs", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ReportRunDetail["run"]>>(
        `/api/v1/reports/runs?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useReportRunDetail(runId: string | undefined) {
  return useQuery({
    queryKey: ["reports", "runs", runId],
    queryFn: () => apiFetchClient<DataResponse<ReportRunDetail>>(`/api/v1/reports/runs/${runId}`),
    select: (response) => response.data,
    enabled: !!runId,
  });
}
