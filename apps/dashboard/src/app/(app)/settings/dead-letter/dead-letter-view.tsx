"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { DeadLetterEntry, DeadLetterResolutionStatus } from "@rkpr/contracts";

import {
  useDeadLetterList,
  useIgnoreDeadLetterEntry,
  useMarkDeadLetterInvestigating,
  useMarkDeadLetterReplayReady,
  useReplayDeadLetterEntry,
} from "@/lib/hooks/use-dead-letter";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { humanize, formatDateTime } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import type { StatusTone } from "@/components/status-badge";
import { PageHeader } from "@/components/page-header";
import { DataTable } from "@/components/data-table/data-table";
import { StatusBadge } from "@/components/status-badge";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const RESOLUTION_STATUSES: DeadLetterResolutionStatus[] = [
  "new",
  "investigating",
  "corrected",
  "replay_ready",
  "replayed",
  "ignored_with_reason",
  "permanently_closed",
];
const RESOLUTION_TONE: Record<DeadLetterResolutionStatus, StatusTone> = {
  new: "danger",
  investigating: "warning",
  corrected: "info",
  replay_ready: "info",
  replayed: "success",
  ignored_with_reason: "neutral",
  permanently_closed: "neutral",
};
const PAGE_SIZE = 25;

export function DeadLetterView() {
  const { data: currentUser } = useCurrentUser();
  const canReplay = hasPermission(currentUser, "dead_letter.replay");
  const [resolutionStatus, setResolutionStatus] = useState<string>("all");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<DeadLetterEntry | null>(null);
  const { data, isLoading } = useDeadLetterList({
    resolutionStatus: resolutionStatus === "all" ? undefined : resolutionStatus,
    page,
    pageSize: PAGE_SIZE,
  });

  const columns = useMemo<ColumnDef<DeadLetterEntry, unknown>[]>(
    () => [
      {
        id: "original_type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="font-mono text-xs">{row.original.original_type}</span>
            <span className="text-muted-foreground text-xs">
              {humanize(row.original.source_type)}
            </span>
          </div>
        ),
      },
      {
        id: "failure_category",
        header: "Failure",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{humanize(row.original.failure_category ?? "unknown")}</span>
        ),
      },
      {
        id: "resolution_status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.resolution_status)}
            tone={RESOLUTION_TONE[row.original.resolution_status]}
          />
        ),
      },
      {
        id: "dead_letter_at",
        header: "Dead-lettered",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground text-sm">
            {formatDateTime(row.original.dead_letter_at)}
          </span>
        ),
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) => (
          <Button size="sm" variant="outline" onClick={() => setSelected(row.original)}>
            Review
          </Button>
        ),
      },
    ],
    [],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Dead Letter Queue"
        description="Jobs and outbox events that exhausted their retry budget — replay requires a human confirmation that the root cause was fixed."
      />

      <Select
        value={resolutionStatus}
        onValueChange={(v) => {
          setResolutionStatus(v);
          setPage(1);
        }}
      >
        <SelectTrigger className="w-52">
          <SelectValue placeholder="Resolution status" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          {RESOLUTION_STATUSES.map((s) => (
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
        emptyTitle="Nothing dead-lettered"
        emptyDescription="Jobs and events that exhaust their retry budget will show up here."
        pagination={
          data
            ? {
                pageIndex: page - 1,
                pageCount: Math.max(1, Math.ceil(data.pagination.total / data.pagination.page_size)),
                total: data.pagination.total,
                pageSize: data.pagination.page_size,
                onPageChange: (pageIndex) => setPage(pageIndex + 1),
              }
            : undefined
        }
      />

      {selected && (
        <DeadLetterDetailModal
          entry={selected}
          canReplay={canReplay}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

function DeadLetterDetailModal({
  entry,
  canReplay,
  onClose,
}: {
  entry: DeadLetterEntry;
  canReplay: boolean;
  onClose: () => void;
}) {
  const [notes, setNotes] = useState(entry.notes ?? "");
  const [error, setError] = useState<string | null>(null);
  const markInvestigating = useMarkDeadLetterInvestigating();
  const markReplayReady = useMarkDeadLetterReplayReady();
  const ignoreEntry = useIgnoreDeadLetterEntry();
  const replayEntry = useReplayDeadLetterEntry();

  const handleError = (err: unknown) =>
    setError(err instanceof ApiError ? err.message : "That action could not be completed.");

  return (
    <Modal open onOpenChange={(open) => !open && onClose()} title={entry.original_type} size="lg">
      <div className="flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between">
          <StatusBadge
            label={humanize(entry.resolution_status)}
            tone={RESOLUTION_TONE[entry.resolution_status]}
          />
          <span className="text-muted-foreground text-xs">
            {formatDateTime(entry.dead_letter_at)}
          </span>
        </div>

        <div>
          <h3 className="mb-1 text-sm font-medium">Final error</h3>
          <p className="text-muted-foreground text-sm">
            {entry.final_error_summary ?? "No error summary recorded."}
          </p>
        </div>

        {entry.attempt_history && entry.attempt_history.length > 0 && (
          <div>
            <h3 className="mb-1 text-sm font-medium">Attempt history</h3>
            <pre className="bg-muted overflow-x-auto rounded-md p-2 text-xs">
              {JSON.stringify(entry.attempt_history, null, 2)}
            </pre>
          </div>
        )}

        {canReplay && (
          <div className="flex flex-col gap-2">
            <h3 className="text-sm font-medium">Resolution notes</h3>
            <Textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="What was the root cause, and how was it fixed?"
              rows={3}
            />
            <div className="flex flex-wrap gap-2">
              {entry.resolution_status === "new" && (
                <Button
                  size="sm"
                  variant="outline"
                  disabled={markInvestigating.isPending}
                  onClick={() => {
                    setError(null);
                    markInvestigating.mutate(entry.id, { onError: handleError });
                  }}
                >
                  Mark investigating
                </Button>
              )}
              {entry.resolution_status !== "replay_ready" &&
                entry.resolution_status !== "replayed" && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={markReplayReady.isPending}
                    onClick={() => {
                      setError(null);
                      markReplayReady.mutate(
                        { entryId: entry.id, notes },
                        { onError: handleError },
                      );
                    }}
                  >
                    Mark replay-ready
                  </Button>
                )}
              {entry.resolution_status === "replay_ready" && (
                <Button
                  size="sm"
                  disabled={replayEntry.isPending}
                  onClick={() => {
                    setError(null);
                    replayEntry.mutate(entry.id, { onSuccess: onClose, onError: handleError });
                  }}
                >
                  {replayEntry.isPending ? "Replaying…" : "Replay now"}
                </Button>
              )}
              {entry.resolution_status !== "ignored_with_reason" && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!notes.trim() || ignoreEntry.isPending}
                  onClick={() => {
                    setError(null);
                    ignoreEntry.mutate(
                      { entryId: entry.id, reason: notes.trim() },
                      { onSuccess: onClose, onError: handleError },
                    );
                  }}
                >
                  Ignore (needs a reason above)
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
