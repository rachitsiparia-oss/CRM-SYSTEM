"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  AiCompletionRequestInput,
  AiRequest,
  AiRequestFeedback,
  AiRequestFeedbackInput,
  DataResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/ai";

export function useCreateAiRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: AiCompletionRequestInput) =>
      apiFetchClient<DataResponse<AiRequest>>(`${BASE}/requests`, {
        method: "POST",
        body: input,
      }),
    onSuccess: (response) => {
      queryClient.setQueryData(["ai", "requests", response.data.id], response);
    },
  });
}

export function useAiRequestDetail(requestId: string | undefined) {
  return useQuery({
    queryKey: ["ai", "requests", requestId],
    queryFn: () => apiFetchClient<DataResponse<AiRequest>>(`${BASE}/requests/${requestId}`),
    select: (response) => response.data,
    enabled: !!requestId,
  });
}

export function useSubmitAiFeedback(requestId: string) {
  return useMutation({
    mutationFn: (input: AiRequestFeedbackInput) =>
      apiFetchClient<DataResponse<AiRequestFeedback>>(`${BASE}/requests/${requestId}/feedback`, {
        method: "POST",
        body: input,
      }),
  });
}
