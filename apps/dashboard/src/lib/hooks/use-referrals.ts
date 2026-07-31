"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  PaginatedResponse,
  ReferralAttributeInput,
  ReferralCode,
  ReferralProgram,
  ReferralProgramCreateInput,
  ReferralProgramStatus,
  ReferralProgramUpdateInput,
  ReferralRelationship,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/referrals";

// --- Programs ---------------------------------------------------------------

export function useReferralPrograms() {
  return useQuery({
    queryKey: ["referrals", "programs"],
    queryFn: () => apiFetchClient<DataResponse<ReferralProgram[]>>(`${BASE}/programs`),
    select: (response) => response.data,
  });
}

export function useCreateReferralProgram() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ReferralProgramCreateInput) =>
      apiFetchClient<DataResponse<ReferralProgram>>(`${BASE}/programs`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["referrals", "programs"] }),
  });
}

export function useUpdateReferralProgram(programId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ReferralProgramUpdateInput) =>
      apiFetchClient<DataResponse<ReferralProgram>>(`${BASE}/programs/${programId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["referrals", "programs"] }),
  });
}

export function useTransitionReferralProgram(programId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (targetStatus: ReferralProgramStatus) =>
      apiFetchClient<DataResponse<ReferralProgram>>(`${BASE}/programs/${programId}/transition`, {
        method: "POST",
        body: { target_status: targetStatus },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["referrals", "programs"] }),
  });
}

export function useIssueReferralCode(programId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { referrer_customer_id: string; expires_at?: string | null }) =>
      apiFetchClient<DataResponse<ReferralCode>>(`${BASE}/programs/${programId}/codes`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["referrals", "codes"] }),
  });
}

export function useReferralCodeDetail(codeValue: string | undefined) {
  return useQuery({
    queryKey: ["referrals", "codes", codeValue],
    queryFn: () => apiFetchClient<DataResponse<ReferralCode>>(`${BASE}/codes/${codeValue}`),
    select: (response) => response.data,
    enabled: !!codeValue,
  });
}

// --- Relationships -----------------------------------------------------------

export interface ReferralRelationshipListParams {
  page: number;
  pageSize: number;
  programId?: string;
  status?: string;
}

export function useReferralRelationships(params: ReferralRelationshipListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.programId) query.set("program_id", params.programId);
  if (params.status) query.set("status", params.status);

  return useQuery({
    queryKey: ["referrals", "relationships", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ReferralRelationship>>(
        `${BASE}/relationships?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

function useInvalidateReferralRelationships() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["referrals", "relationships"] });
}

export function useAttributeReferral() {
  const invalidate = useInvalidateReferralRelationships();
  return useMutation({
    mutationFn: (input: ReferralAttributeInput) =>
      apiFetchClient<DataResponse<ReferralRelationship>>(`${BASE}/relationships/attribute`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useQualifyReferral(relationshipId: string) {
  const invalidate = useInvalidateReferralRelationships();
  return useMutation({
    mutationFn: (qualifyingOrderId: string) =>
      apiFetchClient<DataResponse<ReferralRelationship>>(
        `${BASE}/relationships/${relationshipId}/qualify`,
        { method: "POST", body: { qualifying_order_id: qualifyingOrderId } },
      ),
    onSuccess: invalidate,
  });
}

export function useRejectReferral(relationshipId: string) {
  const invalidate = useInvalidateReferralRelationships();
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<ReferralRelationship>>(
        `${BASE}/relationships/${relationshipId}/reject`,
        { method: "POST", body: { reason } },
      ),
    onSuccess: invalidate,
  });
}

export function useRewardReferral(relationshipId: string) {
  const invalidate = useInvalidateReferralRelationships();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<ReferralRelationship>>(
        `${BASE}/relationships/${relationshipId}/reward`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}
