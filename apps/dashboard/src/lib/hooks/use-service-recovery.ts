"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  ApprovalRule,
  ApprovalRuleCreateInput,
  ApprovalRuleUpdateInput,
  DataResponse,
  PaginatedResponse,
  RecoveryAction,
  RecoveryActionHistoryEntry,
  RecoveryActionProposeInput,
  RecoveryActionRejectInput,
  RecoveryActionReverseInput,
  RecoveryAnalytics,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/service-recovery";

export interface RecoveryActionListParams {
  page: number;
  pageSize: number;
  complaintId?: string;
  customerId?: string;
  status?: string;
  recoveryType?: string;
}

export function useRecoveryActionList(params: RecoveryActionListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.complaintId) query.set("complaint_id", params.complaintId);
  if (params.customerId) query.set("customer_id", params.customerId);
  if (params.status) query.set("status", params.status);
  if (params.recoveryType) query.set("recovery_type", params.recoveryType);

  return useQuery({
    queryKey: ["service-recovery", "actions", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<RecoveryAction>>(`${BASE}/actions?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useRecoveryActionDetail(actionId: string | undefined) {
  return useQuery({
    queryKey: ["service-recovery", "actions", actionId],
    queryFn: () => apiFetchClient<DataResponse<RecoveryAction>>(`${BASE}/actions/${actionId}`),
    select: (response) => response.data,
    enabled: !!actionId,
  });
}

export function useRecoveryActionHistory(actionId: string | undefined) {
  return useQuery({
    queryKey: ["service-recovery", "actions", actionId, "history"],
    queryFn: () =>
      apiFetchClient<DataResponse<RecoveryActionHistoryEntry[]>>(
        `${BASE}/actions/${actionId}/history`,
      ),
    select: (response) => response.data,
    enabled: !!actionId,
  });
}

export function useRecoveryAnalytics() {
  return useQuery({
    queryKey: ["service-recovery", "analytics"],
    queryFn: () => apiFetchClient<DataResponse<RecoveryAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
  });
}

function useInvalidateRecoveryAction(actionId?: string, complaintId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["service-recovery", "actions", "list"] });
    queryClient.invalidateQueries({ queryKey: ["service-recovery", "analytics"] });
    if (actionId)
      queryClient.invalidateQueries({ queryKey: ["service-recovery", "actions", actionId] });
    if (complaintId) queryClient.invalidateQueries({ queryKey: ["complaints", complaintId] });
  };
}

export function useProposeRecoveryAction(complaintId: string) {
  const invalidate = useInvalidateRecoveryAction(undefined, complaintId);
  return useMutation({
    mutationFn: (input: RecoveryActionProposeInput) =>
      apiFetchClient<DataResponse<RecoveryAction>>(
        `/api/v1/complaints/${complaintId}/recovery-actions`,
        { method: "POST", body: input },
      ),
    onSuccess: invalidate,
  });
}

export function useComplaintRecoveryActions(
  complaintId: string | undefined,
  params: { page: number; pageSize: number },
) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  return useQuery({
    queryKey: ["complaints", complaintId, "recovery-actions", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<RecoveryAction>>(
        `/api/v1/complaints/${complaintId}/recovery-actions?${query.toString()}`,
      ),
    enabled: !!complaintId,
    placeholderData: (previous) => previous,
  });
}

export function useApproveRecoveryAction(actionId: string, complaintId?: string) {
  const invalidate = useInvalidateRecoveryAction(actionId, complaintId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<RecoveryAction>>(`${BASE}/actions/${actionId}/approve`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useRejectRecoveryAction(actionId: string, complaintId?: string) {
  const invalidate = useInvalidateRecoveryAction(actionId, complaintId);
  return useMutation({
    mutationFn: (input: RecoveryActionRejectInput) =>
      apiFetchClient<DataResponse<RecoveryAction>>(`${BASE}/actions/${actionId}/reject`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useExecuteRecoveryAction(actionId: string, complaintId?: string) {
  const invalidate = useInvalidateRecoveryAction(actionId, complaintId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<RecoveryAction>>(`${BASE}/actions/${actionId}/execute`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useReverseRecoveryAction(actionId: string, complaintId?: string) {
  const invalidate = useInvalidateRecoveryAction(actionId, complaintId);
  return useMutation({
    mutationFn: (input: RecoveryActionReverseInput) =>
      apiFetchClient<DataResponse<RecoveryAction>>(`${BASE}/actions/${actionId}/reverse`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

// --- Approval rules -------------------------------------------------------

export function useApprovalRuleList(isActive?: boolean) {
  const query = new URLSearchParams();
  if (isActive !== undefined) query.set("is_active", String(isActive));
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return useQuery({
    queryKey: ["service-recovery", "approval-rules", isActive],
    queryFn: () =>
      apiFetchClient<DataResponse<ApprovalRule[]>>(`${BASE}/approval-rules${suffix}`),
    select: (response) => response.data,
  });
}

function useInvalidateApprovalRules() {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({ queryKey: ["service-recovery", "approval-rules"] });
}

export function useCreateApprovalRule() {
  const invalidate = useInvalidateApprovalRules();
  return useMutation({
    mutationFn: (input: ApprovalRuleCreateInput) =>
      apiFetchClient<DataResponse<ApprovalRule>>(`${BASE}/approval-rules`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useUpdateApprovalRule(ruleId: string) {
  const invalidate = useInvalidateApprovalRules();
  return useMutation({
    mutationFn: (input: ApprovalRuleUpdateInput) =>
      apiFetchClient<DataResponse<ApprovalRule>>(`${BASE}/approval-rules/${ruleId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}
