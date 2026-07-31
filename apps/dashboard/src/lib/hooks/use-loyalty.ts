"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  LoyaltyAccount,
  LoyaltyAdjustInput,
  LoyaltyAnalytics,
  LoyaltyEarnInput,
  LoyaltyEnrollInput,
  LoyaltyLedgerEntry,
  LoyaltyProgram,
  LoyaltyProgramCreateInput,
  LoyaltyProgramUpdateInput,
  LoyaltyProgramStatus,
  LoyaltyRedeemInput,
  LoyaltyReverseInput,
  LoyaltyTier,
  LoyaltyTierAssignInput,
  LoyaltyTierCreateInput,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/loyalty";

// --- Programs ---------------------------------------------------------------

export function useLoyaltyPrograms() {
  return useQuery({
    queryKey: ["loyalty", "programs"],
    queryFn: () => apiFetchClient<DataResponse<LoyaltyProgram[]>>(`${BASE}/programs`),
    select: (response) => response.data,
  });
}

export function useCreateLoyaltyProgram() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LoyaltyProgramCreateInput) =>
      apiFetchClient<DataResponse<LoyaltyProgram>>(`${BASE}/programs`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["loyalty", "programs"] }),
  });
}

export function useUpdateLoyaltyProgram(programId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LoyaltyProgramUpdateInput) =>
      apiFetchClient<DataResponse<LoyaltyProgram>>(`${BASE}/programs/${programId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["loyalty", "programs"] }),
  });
}

export function useTransitionLoyaltyProgram(programId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (targetStatus: LoyaltyProgramStatus) =>
      apiFetchClient<DataResponse<LoyaltyProgram>>(`${BASE}/programs/${programId}/transition`, {
        method: "POST",
        body: { target_status: targetStatus },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["loyalty", "programs"] }),
  });
}

// --- Tiers -------------------------------------------------------------------

export function useLoyaltyTiers(programId: string | undefined) {
  return useQuery({
    queryKey: ["loyalty", "tiers", programId],
    queryFn: () =>
      apiFetchClient<DataResponse<LoyaltyTier[]>>(`${BASE}/tiers?program_id=${programId}`),
    select: (response) => response.data,
    enabled: !!programId,
  });
}

export function useCreateLoyaltyTier(programId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LoyaltyTierCreateInput) =>
      apiFetchClient<DataResponse<LoyaltyTier>>(`${BASE}/tiers?program_id=${programId}`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["loyalty", "tiers", programId] }),
  });
}

// --- Accounts and ledger -----------------------------------------------------

export function useLoyaltyAccountForCustomer(customerId: string | undefined, programId?: string) {
  const query = new URLSearchParams({ customer_id: customerId ?? "" });
  if (programId) query.set("program_id", programId);
  return useQuery({
    queryKey: ["loyalty", "accounts", "by-customer", customerId, programId],
    queryFn: () =>
      apiFetchClient<DataResponse<LoyaltyAccount | null>>(`${BASE}/accounts?${query.toString()}`),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

export function useEnrollLoyalty() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: LoyaltyEnrollInput) =>
      apiFetchClient<DataResponse<LoyaltyAccount>>(`${BASE}/accounts`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["loyalty", "accounts"] }),
  });
}

export interface LoyaltyLedgerParams {
  page: number;
  pageSize: number;
}

export function useLoyaltyLedger(accountId: string | undefined, params: LoyaltyLedgerParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  return useQuery({
    queryKey: ["loyalty", "accounts", accountId, "ledger", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<LoyaltyLedgerEntry>>(
        `${BASE}/accounts/${accountId}/ledger?${query.toString()}`,
      ),
    enabled: !!accountId,
    placeholderData: (previous) => previous,
  });
}

function useInvalidateLoyaltyAccounts() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["loyalty"] });
}

export function useEarnLoyaltyPoints() {
  const invalidate = useInvalidateLoyaltyAccounts();
  return useMutation({
    mutationFn: (input: LoyaltyEarnInput) =>
      apiFetchClient<DataResponse<LoyaltyLedgerEntry>>(`${BASE}/earn`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useRedeemLoyaltyPoints() {
  const invalidate = useInvalidateLoyaltyAccounts();
  return useMutation({
    mutationFn: (input: LoyaltyRedeemInput) =>
      apiFetchClient<DataResponse<LoyaltyLedgerEntry>>(`${BASE}/redeem`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAdjustLoyaltyPoints() {
  const invalidate = useInvalidateLoyaltyAccounts();
  return useMutation({
    mutationFn: (input: LoyaltyAdjustInput) =>
      apiFetchClient<DataResponse<LoyaltyLedgerEntry>>(`${BASE}/adjust`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useReverseLoyaltyEntry() {
  const invalidate = useInvalidateLoyaltyAccounts();
  return useMutation({
    mutationFn: (input: LoyaltyReverseInput) =>
      apiFetchClient<DataResponse<LoyaltyLedgerEntry>>(`${BASE}/reverse`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAssignLoyaltyTier(accountId: string) {
  const invalidate = useInvalidateLoyaltyAccounts();
  return useMutation({
    mutationFn: (input: LoyaltyTierAssignInput) =>
      apiFetchClient<DataResponse<LoyaltyAccount>>(`${BASE}/accounts/${accountId}/tier`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

// --- Analytics -----------------------------------------------------------

export function useLoyaltyAnalytics() {
  return useQuery({
    queryKey: ["loyalty", "analytics"],
    queryFn: () => apiFetchClient<DataResponse<LoyaltyAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
  });
}
