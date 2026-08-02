"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  DeadLetterEntry,
  IgnoreEntryInput,
  MarkReplayReadyInput,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/dead-letter";

export function useDeadLetterList(params: {
  resolutionStatus?: string;
  sourceType?: string;
  page: number;
  pageSize: number;
}) {
  const query = new URLSearchParams();
  if (params.resolutionStatus) query.set("resolution_status", params.resolutionStatus);
  if (params.sourceType) query.set("source_type", params.sourceType);
  query.set("page", String(params.page));
  query.set("page_size", String(params.pageSize));
  return useQuery({
    queryKey: ["dead-letter", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<DeadLetterEntry>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useMarkDeadLetterInvestigating() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) =>
      apiFetchClient<DataResponse<DeadLetterEntry>>(`${BASE}/${entryId}/investigate`, {
        method: "POST",
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["dead-letter"] }),
  });
}

export function useMarkDeadLetterReplayReady() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, notes }: { entryId: string } & MarkReplayReadyInput) =>
      apiFetchClient<DataResponse<DeadLetterEntry>>(`${BASE}/${entryId}/mark-replay-ready`, {
        method: "POST",
        body: { notes },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["dead-letter"] }),
  });
}

export function useIgnoreDeadLetterEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ entryId, reason }: { entryId: string } & IgnoreEntryInput) =>
      apiFetchClient<DataResponse<DeadLetterEntry>>(`${BASE}/${entryId}/ignore`, {
        method: "POST",
        body: { reason },
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["dead-letter"] }),
  });
}

export function useReplayDeadLetterEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) =>
      apiFetchClient<DataResponse<DeadLetterEntry>>(`${BASE}/${entryId}/replay`, {
        method: "POST",
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["dead-letter"] }),
  });
}
