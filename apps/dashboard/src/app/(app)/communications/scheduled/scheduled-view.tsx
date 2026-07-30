"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { ScheduledMessage } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import {
  useCancelScheduledMessage,
  useScheduledMessages,
} from "@/lib/hooks/use-communications";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { SCHEDULED_MESSAGE_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScheduledMessageCreateModal } from "./scheduled-message-create-modal";

const ALL = "__all";
const STATUSES = ["scheduled", "processing", "sent", "cancelled", "failed"];

export function ScheduledView() {
  const { data: currentUser } = useCurrentUser();
  const [status, setStatus] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);
  const { data, isLoading } = useScheduledMessages(status === ALL ? undefined : status);
  const cancelScheduled = useCancelScheduledMessage();

  const canManage = hasPermission(currentUser, "communications.reply");

  const columns = useMemo<ColumnDef<ScheduledMessage, unknown>[]>(
    () => [
      {
        id: "purpose",
        header: "Purpose",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.purpose)}</span>,
      },
      {
        id: "recipient",
        header: "Recipient",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.recipient_reference}</span>,
      },
      {
        id: "scheduled_for",
        header: "Scheduled for",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatDateTime(row.original.scheduled_for)}</span>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={SCHEDULED_MESSAGE_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) =>
          canManage && row.original.status === "scheduled" ? (
            <Button
              size="sm"
              variant="outline"
              onClick={() => void cancelScheduled.mutateAsync(row.original.id)}
              disabled={cancelScheduled.isPending}
            >
              Cancel
            </Button>
          ) : null,
      },
    ],
    [canManage, cancelScheduled],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Scheduled messages"
        description="Reservation reminders, feedback requests, and delayed manual messages queued to send."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              Schedule a message
            </Button>
          ) : null
        }
      />

      <Select value={status} onValueChange={setStatus}>
        <SelectTrigger className="w-48" aria-label="Filter by status">
          <SelectValue placeholder="Status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL}>All statuses</SelectItem>
          {STATUSES.map((s) => (
            <SelectItem key={s} value={s}>
              {humanize(s)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <DataTable
        columns={columns}
        data={data?.data ?? []}
        getRowId={(row) => row.id}
        loading={isLoading}
        emptyTitle="No scheduled messages"
        emptyDescription="Schedule the first message to get started."
      />

      <ScheduledMessageCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
