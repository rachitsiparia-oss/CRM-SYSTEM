"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { DataResponse, JobRecord, PaginatedResponse, QueueStat } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/jobs";

export function useJobList(params: {
  status?: string;
  jobType?: string;
  queueName?: string;
  page: number;
  pageSize: number;
}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.jobType) query.set("job_type", params.jobType);
  if (params.queueName) query.set("queue_name", params.queueName);
  query.set("page", String(params.page));
  query.set("page_size", String(params.pageSize));
  return useQuery({
    queryKey: ["jobs", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<JobRecord>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useJobQueueStats() {
  return useQuery({
    queryKey: ["jobs", "queue-stats"],
    queryFn: () => apiFetchClient<DataResponse<QueueStat[]>>(`${BASE}/queue-stats`),
    select: (response) => response.data,
    refetchInterval: 30_000,
  });
}

export function useCancelJob() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      apiFetchClient<DataResponse<JobRecord>>(`${BASE}/${jobId}/cancel`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}
