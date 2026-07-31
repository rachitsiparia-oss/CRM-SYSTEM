"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  CustomerCreditAccount,
  CustomerCreditAdjustInput,
  CustomerCreditAnalytics,
  CustomerCreditIssueInput,
  CustomerCreditLedgerEntry,
  CustomerCreditRedeemInput,
  DataResponse,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/customer-credit";

export function useCustomerCreditAccount(customerId: string | undefined) {
  return useQuery({
    queryKey: ["customer-credit", "accounts", "by-customer", customerId],
    queryFn: () =>
      apiFetchClient<DataResponse<CustomerCreditAccount | null>>(
        `${BASE}/accounts?customer_id=${customerId}`,
      ),
    select: (response) => response.data,
    enabled: !!customerId,
  });
}

export function useEnsureCustomerCreditAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (customerId: string) =>
      apiFetchClient<DataResponse<CustomerCreditAccount>>(`${BASE}/accounts`, {
        method: "POST",
        body: { customer_id: customerId },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["customer-credit", "accounts"] }),
  });
}

export interface CustomerCreditLedgerParams {
  page: number;
  pageSize: number;
}

export function useCustomerCreditLedger(
  accountId: string | undefined,
  params: CustomerCreditLedgerParams,
) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  return useQuery({
    queryKey: ["customer-credit", "accounts", accountId, "ledger", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<CustomerCreditLedgerEntry>>(
        `${BASE}/accounts/${accountId}/ledger?${query.toString()}`,
      ),
    enabled: !!accountId,
    placeholderData: (previous) => previous,
  });
}

function useInvalidateCustomerCredit() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["customer-credit"] });
}

export function useIssueCustomerCredit() {
  const invalidate = useInvalidateCustomerCredit();
  return useMutation({
    mutationFn: (input: CustomerCreditIssueInput) =>
      apiFetchClient<DataResponse<CustomerCreditLedgerEntry>>(`${BASE}/issue`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useRedeemCustomerCredit() {
  const invalidate = useInvalidateCustomerCredit();
  return useMutation({
    mutationFn: (input: CustomerCreditRedeemInput) =>
      apiFetchClient<DataResponse<CustomerCreditLedgerEntry>>(`${BASE}/redeem`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useAdjustCustomerCredit() {
  const invalidate = useInvalidateCustomerCredit();
  return useMutation({
    mutationFn: (input: CustomerCreditAdjustInput) =>
      apiFetchClient<DataResponse<CustomerCreditLedgerEntry>>(`${BASE}/adjust`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useReverseCustomerCreditEntry() {
  const invalidate = useInvalidateCustomerCredit();
  return useMutation({
    mutationFn: (input: { entry_id: string; reason: string; idempotency_key: string }) =>
      apiFetchClient<DataResponse<CustomerCreditLedgerEntry>>(`${BASE}/reverse`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useCustomerCreditAnalytics() {
  return useQuery({
    queryKey: ["customer-credit", "analytics"],
    queryFn: () =>
      apiFetchClient<DataResponse<CustomerCreditAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
  });
}
