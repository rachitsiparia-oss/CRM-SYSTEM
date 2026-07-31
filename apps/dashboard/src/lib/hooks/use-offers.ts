"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  Coupon,
  CouponCreateInput,
  DataResponse,
  Offer,
  OfferCreateInput,
  OfferPreviewInput,
  OfferPreviewResult,
  OfferRedemption,
  OfferReserveRedemptionInput,
  OfferStatus,
  OfferUpdateInput,
  OfferVersionCreateInput,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/offers";

export interface OfferListParams {
  page: number;
  pageSize: number;
  status?: string;
  offerType?: string;
}

export function useOfferList(params: OfferListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.offerType) query.set("offer_type", params.offerType);

  return useQuery({
    queryKey: ["offers", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Offer>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useOfferDetail(offerId: string | undefined) {
  return useQuery({
    queryKey: ["offers", offerId],
    queryFn: () => apiFetchClient<DataResponse<Offer>>(`${BASE}/${offerId}`),
    select: (response) => response.data,
    enabled: !!offerId,
  });
}

function useInvalidateOffer(offerId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["offers", "list"] });
    if (offerId) queryClient.invalidateQueries({ queryKey: ["offers", offerId] });
  };
}

export function useCreateOffer() {
  const invalidate = useInvalidateOffer();
  return useMutation({
    mutationFn: (input: OfferCreateInput) =>
      apiFetchClient<DataResponse<Offer>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useUpdateOffer(offerId: string) {
  const invalidate = useInvalidateOffer(offerId);
  return useMutation({
    mutationFn: (input: OfferUpdateInput) =>
      apiFetchClient<DataResponse<Offer>>(`${BASE}/${offerId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useCreateOfferVersion(offerId: string) {
  const invalidate = useInvalidateOffer(offerId);
  return useMutation({
    mutationFn: (input: OfferVersionCreateInput) =>
      apiFetchClient<DataResponse<Offer>>(`${BASE}/${offerId}/versions`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useTransitionOffer(offerId: string) {
  const invalidate = useInvalidateOffer(offerId);
  return useMutation({
    mutationFn: (targetStatus: OfferStatus) =>
      apiFetchClient<DataResponse<Offer>>(`${BASE}/${offerId}/transition`, {
        method: "POST",
        body: { target_status: targetStatus },
      }),
    onSuccess: invalidate,
  });
}

// --- Coupons -------------------------------------------------------------

export function useOfferCoupons(offerId: string | undefined) {
  return useQuery({
    queryKey: ["offers", offerId, "coupons"],
    queryFn: () => apiFetchClient<DataResponse<Coupon[]>>(`${BASE}/${offerId}/coupons`),
    select: (response) => response.data,
    enabled: !!offerId,
  });
}

export function useCreateCoupon(offerId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CouponCreateInput) =>
      apiFetchClient<DataResponse<Coupon>>(`${BASE}/${offerId}/coupons`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["offers", offerId, "coupons"] }),
  });
}

// --- Preview and redemptions -----------------------------------------------

export function usePreviewOffer(offerId: string) {
  return useMutation({
    mutationFn: (input: OfferPreviewInput) =>
      apiFetchClient<DataResponse<OfferPreviewResult>>(`${BASE}/${offerId}/preview`, {
        method: "POST",
        body: input,
      }),
  });
}

export function useRedemptionDetail(redemptionId: string | undefined) {
  return useQuery({
    queryKey: ["offers", "redemptions", redemptionId],
    queryFn: () =>
      apiFetchClient<DataResponse<OfferRedemption>>(`${BASE}/redemptions/${redemptionId}`),
    select: (response) => response.data,
    enabled: !!redemptionId,
  });
}

function useInvalidateRedemption(redemptionId?: string) {
  const queryClient = useQueryClient();
  return () => {
    if (redemptionId)
      queryClient.invalidateQueries({ queryKey: ["offers", "redemptions", redemptionId] });
    queryClient.invalidateQueries({ queryKey: ["offers", "list"] });
  };
}

export function useReserveRedemption() {
  const invalidate = useInvalidateRedemption();
  return useMutation({
    mutationFn: (input: OfferReserveRedemptionInput) =>
      apiFetchClient<DataResponse<OfferRedemption>>(`${BASE}/redemptions/reserve`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useConfirmRedemption(redemptionId: string) {
  const invalidate = useInvalidateRedemption(redemptionId);
  return useMutation({
    mutationFn: (orderId: string) =>
      apiFetchClient<DataResponse<OfferRedemption>>(
        `${BASE}/redemptions/${redemptionId}/confirm`,
        { method: "POST", body: { order_id: orderId } },
      ),
    onSuccess: invalidate,
  });
}

export function useRejectRedemption(redemptionId: string) {
  const invalidate = useInvalidateRedemption(redemptionId);
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<OfferRedemption>>(`${BASE}/redemptions/${redemptionId}/reject`, {
        method: "POST",
        body: { reason },
      }),
    onSuccess: invalidate,
  });
}

export function useReverseRedemption(redemptionId: string) {
  const invalidate = useInvalidateRedemption(redemptionId);
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<OfferRedemption>>(
        `${BASE}/redemptions/${redemptionId}/reverse`,
        { method: "POST", body: { reason } },
      ),
    onSuccess: invalidate,
  });
}
