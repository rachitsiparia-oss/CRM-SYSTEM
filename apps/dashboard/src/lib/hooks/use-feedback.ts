"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  ConvertToComplaintInput,
  DataResponse,
  Feedback,
  FeedbackAnalytics,
  FeedbackCreateInput,
  FeedbackStatusHistoryEntry,
  FeedbackTransitionInput,
  FeedbackUpdateInput,
  PaginatedResponse,
  RatingOut,
  ReviewRequest,
  ReviewRequestAnalytics,
  ReviewRequestCompleteInput,
  ReviewRequestCreateInput,
  TagAssignInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/feedback";
const REVIEW_REQUESTS_BASE = "/api/v1/review-requests";

export interface FeedbackListParams {
  page: number;
  pageSize: number;
  status?: string;
  source?: string;
  sentiment?: string;
  customerId?: string;
}

export function useFeedbackList(params: FeedbackListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.source) query.set("source", params.source);
  if (params.sentiment) query.set("sentiment", params.sentiment);
  if (params.customerId) query.set("customer_id", params.customerId);

  return useQuery({
    queryKey: ["feedback", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Feedback>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useFeedbackDetail(feedbackId: string | undefined) {
  return useQuery({
    queryKey: ["feedback", feedbackId],
    queryFn: () => apiFetchClient<DataResponse<Feedback>>(`${BASE}/${feedbackId}`),
    select: (response) => response.data,
    enabled: !!feedbackId,
  });
}

export function useFeedbackRatings(feedbackId: string | undefined) {
  return useQuery({
    queryKey: ["feedback", feedbackId, "ratings"],
    queryFn: () => apiFetchClient<DataResponse<RatingOut[]>>(`${BASE}/${feedbackId}/ratings`),
    select: (response) => response.data,
    enabled: !!feedbackId,
  });
}

export function useFeedbackStatusHistory(feedbackId: string | undefined) {
  return useQuery({
    queryKey: ["feedback", feedbackId, "status-history"],
    queryFn: () =>
      apiFetchClient<DataResponse<FeedbackStatusHistoryEntry[]>>(
        `${BASE}/${feedbackId}/status-history`,
      ),
    select: (response) => response.data,
    enabled: !!feedbackId,
  });
}

export function useCustomerFeedbackHistory(
  customerId: string | undefined,
  params: { page: number; pageSize: number },
) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  return useQuery({
    queryKey: ["feedback", "customer-history", customerId, params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<Feedback>>(
        `${BASE}/customers/${customerId}/history?${query.toString()}`,
      ),
    enabled: !!customerId,
    placeholderData: (previous) => previous,
  });
}

export function useFeedbackAnalytics() {
  return useQuery({
    queryKey: ["feedback", "analytics"],
    queryFn: () => apiFetchClient<DataResponse<FeedbackAnalytics>>(`${BASE}/analytics`),
    select: (response) => response.data,
  });
}

function useInvalidateFeedback(feedbackId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["feedback", "list"] });
    queryClient.invalidateQueries({ queryKey: ["feedback", "analytics"] });
    if (feedbackId) queryClient.invalidateQueries({ queryKey: ["feedback", feedbackId] });
  };
}

export function useCreateFeedback() {
  const invalidate = useInvalidateFeedback();
  return useMutation({
    mutationFn: (input: FeedbackCreateInput) =>
      apiFetchClient<DataResponse<Feedback>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useUpdateFeedback(feedbackId: string) {
  const invalidate = useInvalidateFeedback(feedbackId);
  return useMutation({
    mutationFn: (input: FeedbackUpdateInput) =>
      apiFetchClient<DataResponse<Feedback>>(`${BASE}/${feedbackId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useTransitionFeedback(feedbackId: string) {
  const queryClient = useQueryClient();
  const invalidate = useInvalidateFeedback(feedbackId);
  return useMutation({
    mutationFn: (input: FeedbackTransitionInput) =>
      apiFetchClient<DataResponse<Feedback>>(`${BASE}/${feedbackId}/transition`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["feedback", feedbackId, "status-history"] });
    },
  });
}

export function useConvertFeedbackToComplaint(feedbackId: string) {
  const invalidate = useInvalidateFeedback(feedbackId);
  return useMutation({
    mutationFn: (input: ConvertToComplaintInput) =>
      apiFetchClient<DataResponse<{ complaint_id: string }>>(
        `${BASE}/${feedbackId}/convert-to-complaint`,
        { method: "POST", body: input },
      ),
    onSuccess: invalidate,
  });
}

export function useAssignFeedbackTags(feedbackId: string) {
  const invalidate = useInvalidateFeedback(feedbackId);
  return useMutation({
    mutationFn: (input: TagAssignInput) =>
      apiFetchClient<DataResponse<Feedback>>(`${BASE}/${feedbackId}/tags`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

// --- Review requests ---------------------------------------------------------

export interface ReviewRequestListParams {
  page: number;
  pageSize: number;
  status?: string;
  customerId?: string;
}

export function useReviewRequestList(params: ReviewRequestListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.customerId) query.set("customer_id", params.customerId);

  return useQuery({
    queryKey: ["review-requests", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<ReviewRequest>>(
        `${REVIEW_REQUESTS_BASE}?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useReviewRequestDetail(reviewRequestId: string | undefined) {
  return useQuery({
    queryKey: ["review-requests", reviewRequestId],
    queryFn: () =>
      apiFetchClient<DataResponse<ReviewRequest>>(`${REVIEW_REQUESTS_BASE}/${reviewRequestId}`),
    select: (response) => response.data,
    enabled: !!reviewRequestId,
  });
}

export function useReviewRequestAnalytics() {
  return useQuery({
    queryKey: ["review-requests", "analytics"],
    queryFn: () =>
      apiFetchClient<DataResponse<ReviewRequestAnalytics>>(`${REVIEW_REQUESTS_BASE}/analytics`),
    select: (response) => response.data,
  });
}

function useInvalidateReviewRequests(reviewRequestId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["review-requests", "list"] });
    queryClient.invalidateQueries({ queryKey: ["review-requests", "analytics"] });
    if (reviewRequestId)
      queryClient.invalidateQueries({ queryKey: ["review-requests", reviewRequestId] });
  };
}

export function useCreateReviewRequest() {
  const invalidate = useInvalidateReviewRequests();
  return useMutation({
    mutationFn: (input: ReviewRequestCreateInput) =>
      apiFetchClient<DataResponse<ReviewRequest>>(REVIEW_REQUESTS_BASE, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useCompleteReviewRequest(reviewRequestId: string) {
  const invalidate = useInvalidateReviewRequests(reviewRequestId);
  return useMutation({
    mutationFn: (input: ReviewRequestCompleteInput) =>
      apiFetchClient<DataResponse<ReviewRequest>>(
        `${REVIEW_REQUESTS_BASE}/${reviewRequestId}/complete`,
        { method: "POST", body: input },
      ),
    onSuccess: invalidate,
  });
}

export function useCancelReviewRequest(reviewRequestId: string) {
  const invalidate = useInvalidateReviewRequests(reviewRequestId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<ReviewRequest>>(
        `${REVIEW_REQUESTS_BASE}/${reviewRequestId}/cancel`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

export function useProcessPendingReviewRequests() {
  const invalidate = useInvalidateReviewRequests();
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ processed: number }>>(
        `${REVIEW_REQUESTS_BASE}/process-pending`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}
