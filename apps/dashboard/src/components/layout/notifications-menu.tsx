"use client";

import { Bell } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState } from "@/components/empty-state";

/**
 * UI-only notification preview — CLAUDE.md section 15/PROJECT_PLAN.md
 * Phase 4 scope explicitly limits this phase to mock data; the durable
 * notifications table, read/unread state, and delivery live in a later
 * phase. No unread items are shown by default so the empty state is what
 * actually renders until that phase wires this up to real data.
 */
const MOCK_NOTIFICATIONS: { id: string; title: string; description: string }[] = [];

export function NotificationsMenu() {
  const unreadCount = MOCK_NOTIFICATIONS.length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-5" />
          {unreadCount > 0 && (
            <span className="absolute right-1.5 top-1.5 flex size-2 rounded-full bg-destructive" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {MOCK_NOTIFICATIONS.length === 0 ? (
          <div className="p-2">
            <EmptyState
              title="No notifications"
              description="You're all caught up."
              className="border-none p-4"
            />
          </div>
        ) : (
          MOCK_NOTIFICATIONS.map((notification) => (
            <div key={notification.id} className="flex flex-col gap-0.5 px-2 py-1.5 text-sm">
              <span className="font-medium">{notification.title}</span>
              <span className="text-muted-foreground text-xs">{notification.description}</span>
            </div>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
