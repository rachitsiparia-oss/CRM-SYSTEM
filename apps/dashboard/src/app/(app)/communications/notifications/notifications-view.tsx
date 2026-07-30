"use client";

import { useState } from "react";
import { Bell, BellOff } from "lucide-react";

import {
  useDismissNotification,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotificationList,
} from "@/lib/hooks/use-notifications";
import { NOTIFICATION_PRIORITY_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";

const PAGE_SIZE = 25;

export function NotificationsView() {
  const [page, setPage] = useState(1);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const { data, isLoading } = useNotificationList({ page, pageSize: PAGE_SIZE, unreadOnly });
  const markRead = useMarkNotificationRead();
  const dismiss = useDismissNotification();
  const markAllRead = useMarkAllNotificationsRead();

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Notifications"
        description="Operational alerts from reservations, orders, tasks, and conversations assigned to you."
        actions={
          <div className="flex gap-2">
            <Button
              variant={unreadOnly ? "default" : "outline"}
              size="sm"
              onClick={() => {
                setUnreadOnly((prev) => !prev);
                setPage(1);
              }}
            >
              {unreadOnly ? "Showing unread" : "Show unread only"}
            </Button>
            <Button variant="outline" size="sm" onClick={() => void markAllRead.mutateAsync()}>
              Mark all read
            </Button>
          </div>
        }
      />

      {isLoading ? (
        <CardSkeleton />
      ) : !data || data.data.length === 0 ? (
        <EmptyState icon={BellOff} title="No notifications" description="You're all caught up." />
      ) : (
        <ul className="flex flex-col gap-2">
          {data.data.map((notification) => (
            <li
              key={notification.id}
              className={`flex items-start justify-between gap-3 rounded-md border p-3 ${
                notification.read_at ? "" : "bg-accent/40"
              }`}
            >
              <div className="flex items-start gap-3">
                <Bell className="text-muted-foreground mt-0.5 size-4" />
                <div>
                  <p className="text-sm font-medium">{notification.title}</p>
                  {notification.body && (
                    <p className="text-muted-foreground text-sm">{notification.body}</p>
                  )}
                  <div className="mt-1 flex items-center gap-2">
                    <StatusBadge
                      label={humanize(notification.priority)}
                      tone={NOTIFICATION_PRIORITY_TONES[notification.priority]}
                    />
                    <span className="text-muted-foreground text-xs">
                      {formatDateTime(notification.created_at)}
                    </span>
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                {!notification.read_at && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void markRead.mutateAsync(notification.id)}
                  >
                    Mark read
                  </Button>
                )}
                {!notification.dismissed_at && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => void dismiss.mutateAsync(notification.id)}
                  >
                    Dismiss
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {data && data.pagination.total > PAGE_SIZE && (
        <div className="flex justify-center gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={page * PAGE_SIZE >= data.pagination.total}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
