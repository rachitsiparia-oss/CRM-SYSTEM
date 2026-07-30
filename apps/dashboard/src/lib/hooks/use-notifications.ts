"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type {
  DataResponse,
  Notification,
  NotificationBroadcastInput,
  PaginatedResponse,
} from "@rkpr/contracts";
import { apiFetchClient } from "@/lib/api/browser";

const BASE = "/api/v1/notifications";

export function useNotificationList(params: { page: number; pageSize: number; unreadOnly?: boolean }) {
  const query = new URLSearchParams({
    page: String(params.page),
    page_size: String(params.pageSize),
  });
  if (params.unreadOnly) query.set("unread_only", "true");

  return useQuery({
    queryKey: ["notifications", "list", params],
    queryFn: () => apiFetchClient<PaginatedResponse<Notification>>(`${BASE}?${query.toString()}`),
    placeholderData: (previous) => previous,
  });
}

export function useUnreadNotificationCount() {
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => apiFetchClient<DataResponse<number>>(`${BASE}/unread-count`),
    select: (response) => response.data,
    refetchInterval: 30_000,
  });
}

function useInvalidateNotifications() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: ["notifications"] });
  };
}

export function useMarkNotificationRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: (notificationId: string) =>
      apiFetchClient<DataResponse<Notification>>(`${BASE}/${notificationId}/read`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useMarkAllNotificationsRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: () => apiFetchClient<DataResponse<number>>(`${BASE}/read-all`, { method: "POST" }),
    onSuccess: invalidate,
  });
}

export function useDismissNotification() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: (notificationId: string) =>
      apiFetchClient<DataResponse<Notification>>(`${BASE}/${notificationId}/dismiss`, {
        method: "POST",
      }),
    onSuccess: invalidate,
  });
}

export function useBroadcastNotification() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: (input: NotificationBroadcastInput) =>
      apiFetchClient<DataResponse<Notification[]>>(`${BASE}/broadcast`, {
        method: "POST",
        body: input,
      }),
    onSuccess: invalidate,
  });
}
