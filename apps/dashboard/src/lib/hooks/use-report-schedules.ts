"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  PaginatedResponse,
  ReportDeliveryAttempt,
  ScheduledReport,
  ScheduledReportCreateInput,
  ScheduledReportRecipient,
  ScheduledReportRecipientCreateInput,
  SetEnabledInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/report-schedules";

export function useScheduledReportList(page: number, pageSize: number) {
  return useQuery({
    queryKey: ["report-schedules", "list", page, pageSize],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ScheduledReport>>(
        `${BASE}?page=${page}&page_size=${pageSize}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useScheduledReportDetail(scheduledReportId: string | undefined) {
  return useQuery({
    queryKey: ["report-schedules", scheduledReportId],
    queryFn: () => apiFetchClient<DataResponse<ScheduledReport>>(`${BASE}/${scheduledReportId}`),
    select: (response) => response.data,
    enabled: !!scheduledReportId,
  });
}

function useInvalidateScheduledReports() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["report-schedules"] });
}

export function useCreateScheduledReport() {
  const invalidate = useInvalidateScheduledReports();
  return useMutation({
    mutationFn: (input: ScheduledReportCreateInput) =>
      apiFetchClient<DataResponse<ScheduledReport>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useSetScheduledReportEnabled(scheduledReportId: string) {
  const invalidate = useInvalidateScheduledReports();
  return useMutation({
    mutationFn: (input: SetEnabledInput) =>
      apiFetchClient<DataResponse<ScheduledReport>>(`${BASE}/${scheduledReportId}/enabled`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useScheduledReportRecipients(scheduledReportId: string | undefined) {
  return useQuery({
    queryKey: ["report-schedules", scheduledReportId, "recipients"],
    queryFn: () =>
      apiFetchClient<DataResponse<ScheduledReportRecipient[]>>(
        `${BASE}/${scheduledReportId}/recipients`,
      ),
    select: (response) => response.data,
    enabled: !!scheduledReportId,
  });
}

export function useAddScheduledReportRecipient(scheduledReportId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ScheduledReportRecipientCreateInput) =>
      apiFetchClient<DataResponse<ScheduledReportRecipient>>(
        `${BASE}/${scheduledReportId}/recipients`,
        { method: "POST", body: input },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["report-schedules", scheduledReportId, "recipients"],
      }),
  });
}

export function useRunScheduledReportNow(scheduledReportId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<ReportDeliveryAttempt[]>>(
        `${BASE}/${scheduledReportId}/run-now`,
        { method: "POST" },
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["report-schedules", scheduledReportId, "delivery-attempts"],
      }),
  });
}

export function useScheduledReportDeliveryAttempts(
  scheduledReportId: string | undefined,
  page: number,
  pageSize: number,
) {
  return useQuery({
    queryKey: ["report-schedules", scheduledReportId, "delivery-attempts", page, pageSize],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ReportDeliveryAttempt>>(
        `${BASE}/${scheduledReportId}/delivery-attempts?page=${page}&page_size=${pageSize}`,
      ),
    enabled: !!scheduledReportId,
    placeholderData: (previous) => previous,
  });
}
