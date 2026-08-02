"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { DataResponse, SchedulerStatus } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/scheduler";

export function useSchedulerStatus() {
  return useQuery({
    queryKey: ["scheduler", "status"],
    queryFn: () => apiFetchClient<DataResponse<SchedulerStatus>>(BASE),
    select: (response) => response.data,
  });
}

export function useSetSchedulerEnabled() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (schedulerEnabled: boolean) =>
      apiFetchClient<DataResponse<SchedulerStatus>>(BASE, {
        method: "PATCH",
        body: { scheduler_enabled: schedulerEnabled },
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["scheduler"] });
    },
  });
}
