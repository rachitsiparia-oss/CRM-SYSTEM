"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  CommercialRiskFlag,
  CommercialRiskReviewInput,
  DataResponse,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/commercial-risk";

export interface CommercialRiskFlagListParams {
  page: number;
  pageSize: number;
  status?: string;
  flagType?: string;
  customerId?: string;
}

export function useCommercialRiskFlagList(params: CommercialRiskFlagListParams) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.status) query.set("status", params.status);
  if (params.flagType) query.set("flag_type", params.flagType);
  if (params.customerId) query.set("customer_id", params.customerId);

  return useQuery({
    queryKey: ["commercial-risk", "flags", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<CommercialRiskFlag>>(
        `${BASE}/flags?${query.toString()}`,
      ),
    placeholderData: (previous) => previous,
  });
}

export function useCommercialRiskFlagDetail(flagId: string | undefined) {
  return useQuery({
    queryKey: ["commercial-risk", "flags", flagId],
    queryFn: () =>
      apiFetchClient<DataResponse<CommercialRiskFlag>>(`${BASE}/flags/${flagId}`),
    select: (response) => response.data,
    enabled: !!flagId,
  });
}

export function useReviewCommercialRiskFlag(flagId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CommercialRiskReviewInput) =>
      apiFetchClient<DataResponse<CommercialRiskFlag>>(`${BASE}/flags/${flagId}/review`, {
        method: "POST",
        body: input,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["commercial-risk", "flags", "list"] });
      queryClient.invalidateQueries({ queryKey: ["commercial-risk", "flags", flagId] });
    },
  });
}
