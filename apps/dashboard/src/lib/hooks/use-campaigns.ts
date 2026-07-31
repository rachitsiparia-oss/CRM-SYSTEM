"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  Campaign,
  CampaignAnalytics,
  CampaignBuildAudienceResult,
  CampaignCreateInput,
  CampaignLaunchResult,
  CampaignRecipient,
  CampaignStatus,
  CampaignUpdateInput,
  DataResponse,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/campaigns";

export interface CampaignListParams {
  page: number;
  pageSize: number;
  status?: string;
}

export function useCampaignList(params: CampaignListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);

  return useQuery({
    queryKey: ["campaigns", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Campaign>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useCampaignDetail(campaignId: string | undefined) {
  return useQuery({
    queryKey: ["campaigns", campaignId],
    queryFn: () => apiFetchClient<DataResponse<Campaign>>(`${BASE}/${campaignId}`),
    select: (response) => response.data,
    enabled: !!campaignId,
  });
}

function useInvalidateCampaign(campaignId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["campaigns", "list"] });
    if (campaignId) queryClient.invalidateQueries({ queryKey: ["campaigns", campaignId] });
  };
}

export function useCreateCampaign() {
  const invalidate = useInvalidateCampaign();
  return useMutation({
    mutationFn: (input: CampaignCreateInput) =>
      apiFetchClient<DataResponse<Campaign>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useUpdateCampaign(campaignId: string) {
  const invalidate = useInvalidateCampaign(campaignId);
  return useMutation({
    mutationFn: (input: CampaignUpdateInput) =>
      apiFetchClient<DataResponse<Campaign>>(`${BASE}/${campaignId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useTransitionCampaign(campaignId: string) {
  const invalidate = useInvalidateCampaign(campaignId);
  return useMutation({
    mutationFn: (input: { target_status: CampaignStatus; reason?: string | null }) =>
      apiFetchClient<DataResponse<Campaign>>(`${BASE}/${campaignId}/transition`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useBuildCampaignAudience(campaignId: string) {
  const invalidate = useInvalidateCampaign(campaignId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<CampaignBuildAudienceResult>>(
        `${BASE}/${campaignId}/audience/build`,
        { method: "POST" },
      ),
    onSuccess: invalidate,
  });
}

export interface CampaignRecipientParams {
  page: number;
  pageSize: number;
  status?: string;
}

export function useCampaignRecipients(
  campaignId: string | undefined,
  params: CampaignRecipientParams,
) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  return useQuery({
    queryKey: ["campaigns", campaignId, "recipients", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<CampaignRecipient>>(
        `${BASE}/${campaignId}/recipients?${query.toString()}`,
      ),
    enabled: !!campaignId,
    placeholderData: (previous) => previous,
  });
}

export function useLaunchCampaign(campaignId: string) {
  const invalidate = useInvalidateCampaign(campaignId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<CampaignLaunchResult>>(`${BASE}/${campaignId}/launch`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useSyncCampaign(campaignId: string) {
  const invalidate = useInvalidateCampaign(campaignId);
  return useMutation({
    mutationFn: () =>
      apiFetchClient<DataResponse<{ status: string }>>(`${BASE}/${campaignId}/sync`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useCampaignAnalytics(campaignId: string | undefined) {
  return useQuery({
    queryKey: ["campaigns", campaignId, "analytics"],
    queryFn: () =>
      apiFetchClient<DataResponse<CampaignAnalytics>>(`${BASE}/${campaignId}/analytics`),
    select: (response) => response.data,
    enabled: !!campaignId,
  });
}
