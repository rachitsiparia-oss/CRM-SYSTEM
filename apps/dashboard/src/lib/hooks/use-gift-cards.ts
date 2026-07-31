"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  GiftCard,
  GiftCardAdjustInput,
  GiftCardAnalytics,
  GiftCardIssueInput,
  GiftCardIssueResult,
  GiftCardLedgerEntry,
  GiftCardRedeemInput,
  GiftCardRevealCode,
  GiftCardStatusActionInput,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/gift-cards";

export interface GiftCardListParams {
  page: number;
  pageSize: number;
  status?: string;
  customerId?: string;
}

export function useGiftCardList(params: GiftCardListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.customerId) query.set("customer_id", params.customerId);

  return useQuery({
    queryKey: ["gift-cards", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<GiftCard>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useGiftCardDetail(giftCardId: string | undefined) {
  return useQuery({
    queryKey: ["gift-cards", giftCardId],
    queryFn: () => apiFetchClient<DataResponse<GiftCard>>(`${BASE}/${giftCardId}`),
    select: (response) => response.data,
    enabled: !!giftCardId,
  });
}

function useInvalidateGiftCard(giftCardId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["gift-cards", "list"] });
    queryClient.invalidateQueries({ queryKey: ["gift-cards", "analytics"] });
    if (giftCardId) queryClient.invalidateQueries({ queryKey: ["gift-cards", giftCardId] });
  };
}

export function useIssueGiftCard() {
  const invalidate = useInvalidateGiftCard();
  return useMutation({
    mutationFn: (input: GiftCardIssueInput) =>
      apiFetchClient<DataResponse<GiftCardIssueResult>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useRevealGiftCardCode(giftCardId: string) {
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<GiftCardRevealCode>>(`${BASE}/${giftCardId}/reveal`),
  });
}

function useGiftCardStatusAction(giftCardId: string, action: string) {
  const invalidate = useInvalidateGiftCard(giftCardId);
  return useMutation({
    mutationFn: (input: GiftCardStatusActionInput = {}) =>
      apiFetchClient<DataResponse<GiftCard>>(`${BASE}/${giftCardId}/${action}`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useActivateGiftCard(giftCardId: string) {
  return useGiftCardStatusAction(giftCardId, "activate");
}
export function useSuspendGiftCard(giftCardId: string) {
  return useGiftCardStatusAction(giftCardId, "suspend");
}
export function useReinstateGiftCard(giftCardId: string) {
  return useGiftCardStatusAction(giftCardId, "reinstate");
}
export function useCancelGiftCard(giftCardId: string) {
  return useGiftCardStatusAction(giftCardId, "cancel");
}
export function useExpireGiftCard(giftCardId: string) {
  return useGiftCardStatusAction(giftCardId, "expire");
}

export function useAdjustGiftCard(giftCardId: string) {
  const invalidate = useInvalidateGiftCard(giftCardId);
  return useMutation({
    mutationFn: (input: GiftCardAdjustInput) =>
      apiFetchClient<DataResponse<GiftCardLedgerEntry>>(`${BASE}/${giftCardId}/adjust`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export interface GiftCardLedgerParams {
  page: number;
  pageSize: number;
}

export function useGiftCardLedger(giftCardId: string | undefined, params: GiftCardLedgerParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  return useQuery({
    queryKey: ["gift-cards", giftCardId, "ledger", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<GiftCardLedgerEntry>>(
        `${BASE}/${giftCardId}/ledger?${query.toString()}`,
      ),
    enabled: !!giftCardId,
    placeholderData: (previous) => previous,
  });
}

export function useRedeemGiftCard() {
  const invalidate = useInvalidateGiftCard();
  return useMutation({
    mutationFn: (input: GiftCardRedeemInput) =>
      apiFetchClient<DataResponse<GiftCardLedgerEntry>>(`${BASE}/redeem`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useReverseGiftCardEntry() {
  const invalidate = useInvalidateGiftCard();
  return useMutation({
    mutationFn: (input: { entry_id: string; reason: string; idempotency_key: string }) =>
      apiFetchClient<DataResponse<GiftCardLedgerEntry>>(`${BASE}/reverse`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useGiftCardAnalytics() {
  return useQuery({
    queryKey: ["gift-cards", "analytics"],
    queryFn: () => apiFetchClient<DataResponse<GiftCardAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
  });
}
