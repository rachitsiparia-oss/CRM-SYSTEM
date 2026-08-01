"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  ExportArtifact,
  ExportDownload,
  ExportRequestInput,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

export function useCreateExport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ExportRequestInput) =>
      apiFetchClient<DataResponse<ExportArtifact>>("/api/v1/exports", {
        method: "POST",
        body: input,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["exports"] }),
  });
}

export function useExportDetail(artifactId: string | undefined) {
  return useQuery({
    queryKey: ["exports", artifactId],
    queryFn: () => apiFetchClient<DataResponse<ExportArtifact>>(`/api/v1/exports/${artifactId}`),
    select: (response) => response.data,
    enabled: !!artifactId,
    refetchInterval: (query) =>
      query.state.data?.data.status === "generating" || query.state.data?.data.status === "pending"
        ? 2000
        : false,
  });
}

export function useExportDownloadUrl() {
  return useMutation({
    mutationFn: (artifactId: string) =>
      apiFetchClient<DataResponse<ExportDownload>>(`/api/v1/exports/${artifactId}/download`),
  });
}
