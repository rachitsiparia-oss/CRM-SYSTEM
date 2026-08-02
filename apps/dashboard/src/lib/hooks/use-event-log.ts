"use client";

import { useQuery } from "@tanstack/react-query";
import type { OutboxEvent, PaginatedResponse } from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/event-log";

export function useEventLogList(params: {
  status?: string;
  eventType?: string;
  page: number;
  pageSize: number;
}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.eventType) query.set("event_type", params.eventType);
  query.set("page", String(params.page));
  query.set("page_size", String(params.pageSize));
  return useQuery({
    queryKey: ["event-log", "list", params],
    queryFn: () =>
      apiFetchClient<PaginatedResponse<OutboxEvent>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}
