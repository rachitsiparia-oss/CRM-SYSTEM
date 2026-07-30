"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { ManualCallLog } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useCallLogs } from "@/lib/hooks/use-communications";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { CallLogCreateModal } from "./call-log-create-modal";

export function CallLogsView() {
  const { data: currentUser } = useCurrentUser();
  const [showCreate, setShowCreate] = useState(false);
  const { data, isLoading } = useCallLogs();

  const canCreate = hasPermission(currentUser, "communications.call_logs.create");

  const columns = useMemo<ColumnDef<ManualCallLog, unknown>[]>(
    () => [
      {
        id: "direction",
        header: "Direction",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.direction)}
            tone={row.original.direction === "inbound" ? "info" : "neutral"}
          />
        ),
      },
      {
        id: "outcome",
        header: "Outcome",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.outcome)}</span>,
      },
      {
        id: "started_at",
        header: "Started",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.started_at)}</span>,
      },
      {
        id: "duration",
        header: "Duration",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.duration_seconds !== null
              ? `${Math.round(row.original.duration_seconds / 60)} min`
              : "—"}
          </span>
        ),
      },
      {
        id: "follow_up",
        header: "Follow-up",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{row.original.follow_up_required ? "Required" : "—"}</span>
        ),
      },
      {
        id: "notes",
        header: "Notes",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">{row.original.notes ?? "—"}</span>
        ),
      },
    ],
    [],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Call logs"
        description="Manual phone call records — not a telephony integration, just the structured summary staff enter."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              Log a call
            </Button>
          ) : null
        }
      />

      <DataTable
        columns={columns}
        data={data?.data ?? []}
        getRowId={(row) => row.id}
        loading={isLoading}
        emptyTitle="No call logs yet"
        emptyDescription="Log the first manual phone call to get started."
      />

      <CallLogCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
