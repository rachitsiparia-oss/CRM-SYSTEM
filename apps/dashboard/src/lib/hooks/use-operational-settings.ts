"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { DataResponse, OperationalSettings, OperationalSettingsUpdateInput } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/operational-settings";

export function useOperationalSettings() {
  return useQuery({
    queryKey: ["operational-settings"],
    queryFn: () => apiFetchClient<DataResponse<OperationalSettings>>(BASE),
    select: (response) => response.data,
  });
}

export function useUpdateOperationalSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: OperationalSettingsUpdateInput) =>
      apiFetchClient<DataResponse<OperationalSettings>>(BASE, { method: "PATCH", body: input }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["operational-settings"] }),
  });
}
