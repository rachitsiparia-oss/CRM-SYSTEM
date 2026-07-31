"use client";

import { useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { ReferralRelationship } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useReferralPrograms, useReferralRelationships } from "@/lib/hooks/use-referrals";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { REFERRAL_RELATIONSHIP_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { FilterBar } from "@/components/filter-bar";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  QualifyReferralModal,
  RejectReferralModal,
  RewardReferralDialog,
} from "./relationship-action-modals";
import { AttributeReferralModal } from "./attribute-referral-modal";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = ["invited", "attributed", "qualified", "rewarded", "rejected", "cancelled"];

export function RelationshipsView() {
  const { data: currentUser } = useCurrentUser();
  const searchParams = useSearchParams();

  const [page, setPage] = useState(1);
  const [programId, setProgramId] = useState(searchParams.get("programId") ?? ALL);
  const [status, setStatus] = useState(ALL);
  const [searchInput, setSearchInput] = useState("");
  const [showAttribute, setShowAttribute] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [qualifyTarget, setQualifyTarget] = useState<string | null>(null);
  const [rejectTarget, setRejectTarget] = useState<string | null>(null);
  const [rewardTarget, setRewardTarget] = useState<string | null>(null);

  const search = useDebouncedValue(searchInput);
  const { data: programs } = useReferralPrograms();
  const { data, isLoading, isError, refetch } = useReferralRelationships({
    page,
    pageSize: PAGE_SIZE,
    programId: programId === ALL ? undefined : programId,
    status: status === ALL ? undefined : status,
  });

  const filteredRows = useMemo(() => {
    const rows = data?.data ?? [];
    if (!search) return rows;
    const lower = search.toLowerCase();
    return rows.filter(
      (row) =>
        row.referred_identity_key.toLowerCase().includes(lower) ||
        row.referrer_customer_id.toLowerCase().includes(lower),
    );
  }, [data, search]);

  const canReview = hasPermission(currentUser, "referrals.review");
  const canAdjust = hasPermission(currentUser, "referrals.adjust");
  const canManage = hasPermission(currentUser, "referrals.manage");

  const programNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const program of programs ?? []) map.set(program.id, program.name);
    return map;
  }, [programs]);

  const columns = useMemo<ColumnDef<ReferralRelationship, unknown>[]>(
    () => [
      {
        id: "referrer",
        header: "Referrer",
        enableSorting: false,
        cell: ({ row }) => <span className="font-mono text-xs">{row.original.referrer_customer_id}</span>,
      },
      {
        id: "referred",
        header: "Referred contact",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="text-sm">{row.original.referred_identity_key}</span>
            {row.original.referred_customer_id && (
              <span className="text-muted-foreground font-mono text-xs">
                {row.original.referred_customer_id}
              </span>
            )}
          </div>
        ),
      },
      {
        id: "program",
        header: "Program",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{programNameById.get(row.original.program_id) ?? "—"}</span>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={REFERRAL_RELATIONSHIP_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "attributed_at",
        header: "Attributed",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.attributed_at)}</span>,
      },
      {
        id: "actions",
        header: "Actions",
        enableSorting: false,
        cell: ({ row }) => {
          const relationship = row.original;
          return (
            <div className="flex flex-wrap gap-2">
              {canReview && relationship.status === "attributed" && (
                <>
                  <Button size="sm" variant="outline" onClick={() => setQualifyTarget(relationship.id)}>
                    Qualify
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => setRejectTarget(relationship.id)}>
                    Reject
                  </Button>
                </>
              )}
              {canAdjust && relationship.status === "qualified" && (
                <Button size="sm" onClick={() => setRewardTarget(relationship.id)}>
                  Reward
                </Button>
              )}
            </div>
          );
        },
      },
    ],
    [canAdjust, canReview, programNameById],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <Link href="/marketing/referrals" className="text-muted-foreground text-sm hover:underline">
          ← Referral programs
        </Link>
      </div>

      <PageHeader
        title="Referral relationships"
        description="Every referral attribution and its qualification/reward status."
        actions={
          canManage ? (
            <Button onClick={() => setShowAttribute(true)}>
              <Plus className="size-4" />
              Attribute referral
            </Button>
          ) : null
        }
      />

      {actionError && (
        <p role="alert" className="text-destructive text-sm">
          {actionError}
        </p>
      )}

      <FilterBar
        search={searchInput}
        onSearchChange={(value) => {
          setSearchInput(value);
          setPage(1);
        }}
        searchPlaceholder="Search referrer or referred contact…"
        hasActiveFilters={!!search || programId !== ALL || status !== ALL}
        onReset={() => {
          setSearchInput("");
          setProgramId(ALL);
          setStatus(ALL);
          setPage(1);
        }}
        filters={
          <div className="flex flex-wrap gap-2">
            <Select
              value={programId}
              onValueChange={(value) => {
                setProgramId(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-56" aria-label="Filter by program">
                <SelectValue placeholder="Program" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All programs</SelectItem>
                {(programs ?? []).map((program) => (
                  <SelectItem key={program.id} value={program.id}>
                    {program.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={status}
              onValueChange={(value) => {
                setStatus(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44" aria-label="Filter by status">
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
          </div>
        }
      />

      {isError ? (
        <ErrorState title="Could not load referral relationships" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRows}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No referral relationships match these filters"
          emptyDescription={
            search || programId !== ALL || status !== ALL
              ? "Try clearing the filters."
              : "Relationships appear once a referral code is shared and used."
          }
          pagination={{
            pageIndex: page - 1,
            pageCount,
            total: data?.pagination.total ?? 0,
            pageSize: PAGE_SIZE,
            onPageChange: (pageIndex) => setPage(pageIndex + 1),
          }}
        />
      )}

      <AttributeReferralModal open={showAttribute} onOpenChange={setShowAttribute} />

      {qualifyTarget && (
        <QualifyReferralModal
          open={!!qualifyTarget}
          onOpenChange={(next) => !next && setQualifyTarget(null)}
          relationshipId={qualifyTarget}
        />
      )}
      {rejectTarget && (
        <RejectReferralModal
          open={!!rejectTarget}
          onOpenChange={(next) => !next && setRejectTarget(null)}
          relationshipId={rejectTarget}
        />
      )}
      {rewardTarget && (
        <RewardReferralDialog
          open={!!rewardTarget}
          onOpenChange={(next) => !next && setRewardTarget(null)}
          relationshipId={rewardTarget}
          onError={(message) => {
            setActionError(message);
            setRewardTarget(null);
          }}
        />
      )}
    </div>
  );
}
