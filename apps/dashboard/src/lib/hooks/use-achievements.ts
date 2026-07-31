"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  Achievement,
  AchievementAward,
  AchievementCreateInput,
  AchievementUpdateInput,
  DataResponse,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/achievements";

export interface AchievementListParams {
  page: number;
  pageSize: number;
  isActive?: boolean;
}

export function useAchievementList(params: AchievementListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.isActive !== undefined) query.set("is_active", String(params.isActive));

  return useQuery({
    queryKey: ["achievements", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Achievement>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useAchievementDetail(achievementId: string | undefined) {
  return useQuery({
    queryKey: ["achievements", achievementId],
    queryFn: () => apiFetchClient<DataResponse<Achievement>>(`${BASE}/${achievementId}`),
    select: (response) => response.data,
    enabled: !!achievementId,
  });
}

function useInvalidateAchievement(achievementId?: string) {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["achievements", "list"] });
    if (achievementId)
      queryClient.invalidateQueries({ queryKey: ["achievements", achievementId] });
  };
}

export function useCreateAchievement() {
  const invalidate = useInvalidateAchievement();
  return useMutation({
    mutationFn: (input: AchievementCreateInput) =>
      apiFetchClient<DataResponse<Achievement>>(BASE, { method: "POST", body: input }),
    onSuccess: invalidate,
  });
}

export function useUpdateAchievement(achievementId: string) {
  const invalidate = useInvalidateAchievement(achievementId);
  return useMutation({
    mutationFn: (input: AchievementUpdateInput) =>
      apiFetchClient<DataResponse<Achievement>>(`${BASE}/${achievementId}`, {
        method: "PATCH",
        body: input,
      }),
    onSuccess: invalidate,
  });
}

export function useEvaluateAchievement() {
  return useMutation({
    mutationFn: (input: {
      achievement_id: string;
      customer_id: string;
      source_event_type: string;
      source_event_key: string;
    }) =>
      apiFetchClient<DataResponse<AchievementAward>>(`${BASE}/evaluate`, {
        method: "POST",
        body: input,
      }),
  });
}

export function useAwardDetail(awardId: string | undefined) {
  return useQuery({
    queryKey: ["achievements", "awards", awardId],
    queryFn: () => apiFetchClient<DataResponse<AchievementAward>>(`${BASE}/awards/${awardId}`),
    select: (response) => response.data,
    enabled: !!awardId,
  });
}

export function useReverseAward(awardId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (reason: string) =>
      apiFetchClient<DataResponse<AchievementAward>>(`${BASE}/awards/${awardId}/reverse`, {
        method: "POST",
        body: { reason },
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["achievements", "awards", awardId] }),
  });
}
