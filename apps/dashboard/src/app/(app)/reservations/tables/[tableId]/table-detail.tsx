"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { TableStatus } from "@rkpr/contracts";
import { ArrowLeft } from "lucide-react";

import {
  useDiningAreas,
  useMergeTables,
  useReleaseTableBlock,
  useSplitTables,
  useTableBlocks,
  useTableDetail,
  useTables,
  useTransitionTableStatus,
} from "@/lib/hooks/use-reservations";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { TABLE_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Mirrors app.reservations.tables.ALLOWED_TABLE_STATUS_TRANSITIONS.
 * `merged` is deliberately excluded — only the merge/split actions below
 * may set or clear it. */
const ALLOWED_TRANSITIONS: Record<TableStatus, TableStatus[]> = {
  available: ["reserved", "occupied", "cleaning", "blocked", "maintenance"],
  reserved: ["occupied", "available", "blocked"],
  occupied: ["cleaning", "available", "blocked"],
  cleaning: ["available", "blocked", "maintenance"],
  blocked: ["available", "maintenance"],
  maintenance: ["available"],
  merged: [],
};

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function TableDetail({ tableId }: { tableId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: table, isLoading, isError, refetch } = useTableDetail(tableId);
  const { data: diningAreas } = useDiningAreas();
  const { data: allTables } = useTables();
  const { data: blocks } = useTableBlocks(tableId);

  const transitionStatus = useTransitionTableStatus(tableId);
  const mergeTables = useMergeTables(tableId);
  const splitTables = useSplitTables(tableId);
  const releaseBlock = useReleaseTableBlock(tableId);

  const [mergeTargetId, setMergeTargetId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const canManage = hasPermission(currentUser, "reservations.tables.manage");

  const diningAreaName = useMemo(
    () => new Map((diningAreas ?? []).map((a) => [a.id, a.name])),
    [diningAreas],
  );
  const mergedInto = (allTables ?? []).filter((t) => t.merged_with_table_id === tableId);
  const mergeCandidates = (allTables ?? []).filter(
    (t) => t.id !== tableId && t.status !== "merged" && t.is_active,
  );

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !table) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Table not found"
          description="This table may not exist, or you may not have access to it."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const available = ALLOWED_TRANSITIONS[table.status];

  async function applyTransition(target: TableStatus) {
    setError(null);
    try {
      await transitionStatus.mutateAsync({ newStatus: target });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The status could not be changed.");
    }
  }

  async function handleMerge() {
    setError(null);
    if (!mergeTargetId) return;
    try {
      await mergeTables.mutateAsync({ secondaryTableIds: [mergeTargetId] });
      setMergeTargetId("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "These tables could not be merged.");
    }
  }

  async function handleSplit() {
    setError(null);
    try {
      await splitTables.mutateAsync(undefined);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "This table could not be split.");
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/reservations/tables"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Tables & Floor
        </Link>
      </div>

      <PageHeader
        title={table.table_number}
        description={diningAreaName.get(table.dining_area_id) ?? ""}
        actions={
          <StatusBadge label={humanize(table.status)} tone={TABLE_STATUS_TONES[table.status]} />
        }
      />

      <SectionCard title="Table details">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Capacity" value={String(table.capacity)} />
          <Field label="Minimum capacity" value={String(table.minimum_capacity ?? "—")} />
          <Field label="Maximum capacity" value={String(table.maximum_capacity ?? "—")} />
          <Field label="Shape" value={humanize(table.shape)} />
          <Field label="Wheelchair accessible" value={table.is_wheelchair_accessible ? "Yes" : "No"} />
          <Field label="Temporary" value={table.is_temporary ? "Yes" : "No"} />
        </dl>
      </SectionCard>

      {canManage && (
        <SectionCard
          title="Table status"
          description={`Currently ${humanize(table.status).toLowerCase()}.`}
        >
          {table.status === "merged" ? (
            <p className="text-muted-foreground text-sm">
              This table is merged into another group — split it before changing its status.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {available.map((target) => (
                <Button
                  key={target}
                  variant="outline"
                  disabled={transitionStatus.isPending}
                  onClick={() => void applyTransition(target)}
                >
                  {humanize(target)}
                </Button>
              ))}
            </div>
          )}
          {error && (
            <p role="alert" className="text-destructive mt-3 text-sm">
              {error}
            </p>
          )}
        </SectionCard>
      )}

      {canManage && (
        <SectionCard
          title="Merge & split"
          description="Combine this table with another for a large party, then split them apart again."
        >
          {mergedInto.length > 0 ? (
            <div className="flex flex-col gap-3">
              <p className="text-sm">
                Currently merged with: {mergedInto.map((t) => t.table_number).join(", ")}
              </p>
              <Button
                variant="outline"
                disabled={splitTables.isPending}
                onClick={() => void handleSplit()}
                className="w-fit"
              >
                {splitTables.isPending ? "Splitting…" : "Split tables"}
              </Button>
            </div>
          ) : (
            <div className="flex flex-wrap items-end gap-3">
              <Select value={mergeTargetId} onValueChange={setMergeTargetId}>
                <SelectTrigger className="w-56" aria-label="Table to merge with">
                  <SelectValue placeholder="Select a table to merge" />
                </SelectTrigger>
                <SelectContent>
                  {mergeCandidates.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.table_number} (seats {t.capacity})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                disabled={!mergeTargetId || mergeTables.isPending}
                onClick={() => void handleMerge()}
              >
                {mergeTables.isPending ? "Merging…" : "Merge"}
              </Button>
            </div>
          )}
        </SectionCard>
      )}

      <SectionCard title="Active blocks" description="Cleaning, maintenance, and private-event holds.">
        {!blocks || blocks.length === 0 ? (
          <EmptyState title="No active blocks" description="This table has no active blocks right now." />
        ) : (
          <ul className="flex flex-col gap-2">
            {blocks.map((block) => (
              <li key={block.id} className="flex items-center justify-between rounded-md border p-3">
                <div>
                  <p className="text-sm font-medium">{humanize(block.block_type)}</p>
                  <p className="text-muted-foreground text-xs">
                    {formatDateTime(block.starts_at)} – {formatDateTime(block.ends_at)}
                  </p>
                  {block.reason && <p className="text-muted-foreground text-xs">{block.reason}</p>}
                </div>
                {canManage && (
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={releaseBlock.isPending}
                    onClick={() => void releaseBlock.mutateAsync(block.id)}
                  >
                    Release
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
