"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  PaginatedResponse,
  Segment,
  SegmentCreateInput,
  SegmentMembership,
  SegmentPreview,
  SegmentRefreshResult,
  SegmentStatus,
  SegmentUpdateInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/segments";

export interface SegmentListParams {
  page: number;
  pageSize: number;
  status?: string;
  segmentType?: string;
}

export function useSegmentList(params: SegmentListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.segmentType) query.set("segment_type", params.segmentType);

  return useQuery({
    queryKey: ["segments", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Segment>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useSegmentDetail(segmentId: string | undefined) {
  return useQuery({
    queryKey: ["segments", segmentId],
    queryFn: () => apiFetchClient<DataResponse<Segment>>(`${BASE}/${segmentId}`),
    select: (response) => response.data,
    enabled: !!segmentId,
  });
}

function useInvalidateSegment(segmentId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["segments", "list"] });
    if (segmentId) queryClient.invalidateQueries({ queryKey: ["segments", segmentId] });
  };
}

export function useCreateSegment() {
  const invalidate = useInvalidateSegment();
  return useMutation({
    mutationFn: (input: SegmentCreateInput) =>
      apiFetchClient<DataResponse<Segment>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useUpdateSegment(segmentId: string) {
  const invalidate = useInvalidateSegment(segmentId);
  return useMutation({
    mutationFn: (input: SegmentUpdateInput) =>
      apiFetchClient<DataResponse<Segment>>(`${BASE}/${segmentId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useTransitionSegment(segmentId: string) {
  const invalidate = useInvalidateSegment(segmentId);
  return useMutation({
    mutationFn: (targetStatus: SegmentStatus) =>
      apiFetchClient<DataResponse<Segment>>(`${BASE}/${segmentId}/transition`, {
        method: "POST",
        body: { target_status: targetStatus },
      }),
    onSuccess: invalidate,
  });
}

export interface SegmentMembersParams {
  page: number;
  pageSize: number;
}

/** `GET /{segment_id}/members` returns the segment's *current* membership as
 * bare customer ids (`PaginatedResponse<string>`) — distinct from
 * `SegmentMembership`, which is the add/remove *event* record returned by
 * the mutation endpoints below. */
export function useSegmentMembers(segmentId: string | undefined, params: SegmentMembersParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  return useQuery({
    queryKey: ["segments", segmentId, "members", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<string>>(
        `${BASE}/${segmentId}/members?${query.toString()}`,
      ),
    enabled: !!segmentId,
    placeholderData: (previous) => previous,
  });
}

export function useAddSegmentMember(segmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { customer_id: string; reason?: string | null }) =>
      apiFetchClient<DataResponse<SegmentMembership>>(`${BASE}/${segmentId}/members`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["segments", segmentId, "members"] }),
  });
}

export function useRemoveSegmentMember(segmentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { customer_id: string; reason?: string | null }) =>
      apiFetchClient<DataResponse<SegmentMembership>>(`${BASE}/${segmentId}/members/remove`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["segments", segmentId, "members"] }),
  });
}

export function useRefreshSegment(segmentId: string) {
  const invalidate = useInvalidateSegment(segmentId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<SegmentRefreshResult>>(`${BASE}/${segmentId}/refresh`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useSegmentPreview(segmentId: string | undefined, customerId: string | undefined) {
  return useQuery({
    queryKey: ["segments", segmentId, "preview", customerId],
    queryFn: () =>
      apiFetchClient<DataResponse<SegmentPreview>>(
        `${BASE}/${segmentId}/preview?customer_id=${customerId}`,
      ),
    select: (response) => response.data,
    enabled: !!segmentId && !!customerId,
  });
}
