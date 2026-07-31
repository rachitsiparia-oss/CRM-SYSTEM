"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { CommercialRiskFlag } from "@rkpr/contracts";

import { useCommercialRiskFlagList } from "@/lib/hooks/use-commercial-risk";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { COMMERCIAL_RISK_FLAG_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
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
import { ReviewFlagModal } from "./review-flag-modal";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = ["open", "reviewing", "resolved", "dismissed"];
const FLAG_TYPES = [
  "repeated_manual_adjustment",
  "repeated_reversal",
  "excessive_coupon_failures",
  "high_value_issuance",
  "self_referral_attempt",
  "identity_overlap",
  "duplicate_attempt",
];

export function RiskQueue() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [customerIdInput, setCustomerIdInput] = useState("");
  const [status, setStatus] = useState(ALL);
  const [flagType, setFlagType] = useState(ALL);
  const [reviewTarget, setReviewTarget] = useState<CommercialRiskFlag | null>(null);

  const customerId = useDebouncedValue(customerIdInput);
  const canReview = hasPermission(currentUser, "commercial_risk.review");

  const { data, isLoading, isError, refetch } = useCommercialRiskFlagList({
    page,
    pageSize: PAGE_SIZE,
    status: status === ALL ? undefined : status,
    flagType: flagType === ALL ? undefined : flagType,
    customerId: customerId || undefined,
  });

  const columns = useMemo<ColumnDef<CommercialRiskFlag, unknown>[]>(
    () => [
      {
        id: "flag_type",
        header: "Flag type",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm font-medium">{humanize(row.original.flag_type)}</span>,
      },
      {
        id: "summary",
        header: "Summary",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.summary}</span>,
      },
      {
        id: "customer",
        header: "Customer",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="font-mono text-xs">{row.original.customer_id ?? "—"}</span>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={COMMERCIAL_RISK_FLAG_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "created_at",
        header: "Flagged",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.created_at)}</span>,
      },
      {
        id: "actions",
        header: "",
        enableSorting: false,
        cell: ({ row }) =>
          canReview && row.original.status !== "resolved" && row.original.status !== "dismissed" ? (
            <Button size="sm" variant="outline" onClick={() => setReviewTarget(row.original)}>
              Review
            </Button>
          ) : null,
      },
    ],
    [canReview],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Commercial risk queue"
        description="Lightweight review queue for flagged commercial-growth events — repeated adjustments, self-referrals, coupon abuse, and similar patterns."
      />

      <FilterBar
        search={customerIdInput}
        onSearchChange={(value) => {
          setCustomerIdInput(value);
          setPage(1);
        }}
        searchPlaceholder="Filter by customer ID…"
        hasActiveFilters={!!customerId || status !== ALL || flagType !== ALL}
        onReset={() => {
          setCustomerIdInput("");
          setStatus(ALL);
          setFlagType(ALL);
          setPage(1);
        }}
        filters={
          <div className="flex flex-wrap gap-2">
            <Select
              value={status}
              onValueChange={(value) => {
                setStatus(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-40" aria-label="Filter by status">
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
            <Select
              value={flagType}
              onValueChange={(value) => {
                setFlagType(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-56" aria-label="Filter by flag type">
                <SelectValue placeholder="Flag type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All flag types</SelectItem>
                {FLAG_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {humanize(t)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        }
      />

      {isError ? (
        <ErrorState title="Could not load flagged events" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No flagged events match these filters"
          emptyDescription={
            customerId || status !== ALL || flagType !== ALL
              ? "Try clearing the filters."
              : "Flags appear automatically when a commercial-growth rule detects a risky pattern."
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

      {reviewTarget && (
        <ReviewFlagModal
          open={!!reviewTarget}
          onOpenChange={(next) => !next && setReviewTarget(null)}
          flagId={reviewTarget.id}
          currentStatus={reviewTarget.status}
        />
      )}
    </div>
  );
}
