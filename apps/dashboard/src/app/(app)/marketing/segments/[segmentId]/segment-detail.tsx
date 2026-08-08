"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { SegmentStatus } from "@rkpr/contracts";

import {
  useAddSegmentMember,
  useRefreshSegment,
  useRemoveSegmentMember,
  useSegmentDetail,
  useSegmentMembers,
  useTransitionSegment,
} from "@/lib/hooks/use-segments";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { SEGMENT_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/data-table/data-table";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { RotateCw } from "lucide-react";

const SEGMENT_TRANSITIONS: Record<SegmentStatus, SegmentStatus[]> = {
  draft: ["active", "archived"],
  active: ["archived"],
  archived: [],
};

const PAGE_SIZE = 25;

export function SegmentDetail({ segmentId }: { segmentId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: segment, isLoading, isError, refetch } = useSegmentDetail(segmentId);
  const [page, setPage] = useState(1);
  const { data: members, isLoading: membersLoading } = useSegmentMembers(segmentId, {
    page,
    pageSize: PAGE_SIZE,
  });

  const transitionSegment = useTransitionSegment(segmentId);
  const refreshSegment = useRefreshSegment(segmentId);
  const addMember = useAddSegmentMember(segmentId);
  const removeMember = useRemoveSegmentMember(segmentId);

  const [error, setError] = useState<string | null>(null);
  const [newMemberId, setNewMemberId] = useState("");

  const canManage = hasPermission(currentUser, "segments.manage");
  const canRefresh = hasPermission(currentUser, "segments.refresh");

  const columns = useMemo<ColumnDef<string, unknown>[]>(
    () => [
      {
        id: "customer_id",
        header: "Customer ID",
        enableSorting: false,
        cell: ({ row }) => <span className="font-mono text-sm">{row.original}</span>,
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) =>
          canManage && segment?.segment_type === "static" ? (
            <Button
              size="sm"
              variant="ghost"
              disabled={removeMember.isPending}
              onClick={() => {
                setError(null);
                removeMember.mutate(
                  { customer_id: row.original },
                  { onError: (err) => setError(err instanceof ApiError ? err.message : "Could not remove this member.") },
                );
              }}
            >
              Remove
            </Button>
          ) : null,
      },
    ],
    [canManage, segment?.segment_type, removeMember],
  );

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">Loading…</div>;
  if (isError || !segment) {
    return (
      <div className="p-6">
        <ErrorState title="Could not load this segment" onRetry={() => void refetch()} />
      </div>
    );
  }

  const availableTransitions = SEGMENT_TRANSITIONS[segment.status];
  const pageCount = members ? Math.max(1, Math.ceil(members.pagination.total / PAGE_SIZE)) : 0;

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link href="/marketing/segments" className="text-sm text-muted-foreground hover:underline">
          ← Segments
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-semibold">{segment.name}</h1>
          <StatusBadge label={humanize(segment.status)} tone={SEGMENT_STATUS_TONES[segment.status]} />
          <Badge variant="secondary" className="capitalize">
            {segment.segment_type}
          </Badge>
        </div>
        <p className="text-muted-foreground text-sm">{segment.code}</p>
        {segment.description && <p className="mt-1 text-sm">{segment.description}</p>}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex flex-wrap gap-2">
        {canManage &&
          availableTransitions.map((target) => (
            <Button
              key={target}
              size="sm"
              variant={target === "archived" ? "outline" : "default"}
              disabled={transitionSegment.isPending}
              onClick={() =>
                transitionSegment.mutate(target, {
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "That action could not be completed."),
                })
              }
            >
              Move to {humanize(target)}
            </Button>
          ))}
        {canRefresh && segment.segment_type === "dynamic" && (
          <Button
            size="sm"
            variant="outline"
            disabled={refreshSegment.isPending}
            onClick={() =>
              refreshSegment.mutate(undefined, {
                onError: (err) =>
                  setError(err instanceof ApiError ? err.message : "Could not refresh this segment."),
              })
            }
          >
            <RotateCw className="size-4" />
            Refresh
          </Button>
        )}
      </div>

      <SectionCard
        title="Membership"
        description={
          segment.last_refreshed_at
            ? `Last refreshed ${formatDateTime(segment.last_refreshed_at)} · ${segment.last_computed_count ?? 0} members`
            : "Not refreshed yet."
        }
        actions={
          canManage && segment.segment_type === "static" ? (
            <div className="flex items-center gap-2">
              <Input
                className="h-8 w-56"
                placeholder="Customer ID"
                value={newMemberId}
                onChange={(e) => setNewMemberId(e.target.value)}
              />
              <Button
                size="sm"
                disabled={!newMemberId.trim() || addMember.isPending}
                onClick={() => {
                  setError(null);
                  addMember.mutate(
                    { customer_id: newMemberId.trim() },
                    {
                      onSuccess: () => setNewMemberId(""),
                      onError: (err) =>
                        setError(err instanceof ApiError ? err.message : "Could not add this member."),
                    },
                  );
                }}
              >
                Add member
              </Button>
            </div>
          ) : undefined
        }
      >
        <DataTable
          columns={columns}
          data={members?.data ?? []}
          getRowId={(row) => row}
          loading={membersLoading}
          emptyTitle="No members yet"
          emptyDescription={
            segment.segment_type === "dynamic"
              ? "Run a refresh to materialize the current membership."
              : "Add the first member by customer ID."
          }
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: members?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      </SectionCard>
    </div>
  );
}
