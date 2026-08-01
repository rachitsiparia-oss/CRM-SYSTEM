"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Feedback } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useFeedbackList } from "@/lib/hooks/use-feedback";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { FEEDBACK_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
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
import { CreateFeedbackModal } from "./create-feedback-modal";
import { FeedbackDetailDrawer } from "./feedback-detail-drawer";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = [
  "new",
  "acknowledged",
  "under_review",
  "action_required",
  "resolved",
  "closed",
  "spam",
];
const SENTIMENTS = ["positive", "neutral", "negative", "mixed"];

export function FeedbackList() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState(ALL);
  const [sentimentFilter, setSentimentFilter] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedFeedbackId, setSelectedFeedbackId] = useState<string | undefined>(undefined);

  const search = useDebouncedValue(searchInput);
  const canCreate = hasPermission(currentUser, "feedback.create");

  const { data, isLoading, isError, refetch } = useFeedbackList({
    page,
    pageSize: PAGE_SIZE,
    status: statusFilter === ALL ? undefined : statusFilter,
    sentiment: sentimentFilter === ALL ? undefined : sentimentFilter,
  });

  const filteredRows = useMemo(() => {
    const rows = data?.data ?? [];
    if (!search) return rows;
    const lower = search.toLowerCase();
    return rows.filter(
      (row) =>
        row.feedback_number.toLowerCase().includes(lower) ||
        (row.comment?.toLowerCase().includes(lower) ?? false),
    );
  }, [data, search]);

  const columns = useMemo<ColumnDef<Feedback, unknown>[]>(
    () => [
      {
        id: "feedback_number",
        header: "Feedback",
        enableSorting: false,
        cell: ({ row }) => (
          <button
            type="button"
            className="font-medium hover:underline"
            onClick={() => setSelectedFeedbackId(row.original.id)}
          >
            {row.original.feedback_number}
          </button>
        ),
      },
      {
        id: "source",
        header: "Source",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.source)}</span>,
      },
      {
        id: "comment",
        header: "Comment",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground max-w-xs truncate text-sm">
            {row.original.comment ?? "—"}
          </span>
        ),
      },
      {
        id: "sentiment",
        header: "Sentiment",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.sentiment ? (
            <StatusBadge
              label={humanize(row.original.sentiment)}
              tone={
                row.original.sentiment === "positive"
                  ? "success"
                  : row.original.sentiment === "negative"
                    ? "danger"
                    : "neutral"
              }
            />
          ) : (
            <span className="text-muted-foreground text-sm">—</span>
          ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={FEEDBACK_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "created_at",
        header: "Created",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatDateTime(row.original.created_at)}</span>
        ),
      },
    ],
    [],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const hasActiveFilters = !!search || statusFilter !== ALL || sentimentFilter !== ALL;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <FilterBar
          search={searchInput}
          onSearchChange={(value) => {
            setSearchInput(value);
            setPage(1);
          }}
          searchPlaceholder="Search number or comment…"
          hasActiveFilters={hasActiveFilters}
          onReset={() => {
            setSearchInput("");
            setStatusFilter(ALL);
            setSentimentFilter(ALL);
            setPage(1);
          }}
          filters={
            <>
              <Select
                value={statusFilter}
                onValueChange={(v) => {
                  setStatusFilter(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-44" aria-label="Filter by status">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>All statuses</SelectItem>
                  {STATUSES.map((status) => (
                    <SelectItem key={status} value={status}>
                      {humanize(status)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={sentimentFilter}
                onValueChange={(v) => {
                  setSentimentFilter(v);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-40" aria-label="Filter by sentiment">
                  <SelectValue placeholder="Sentiment" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>All sentiments</SelectItem>
                  {SENTIMENTS.map((sentiment) => (
                    <SelectItem key={sentiment} value={sentiment}>
                      {humanize(sentiment)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          }
        />
        {canCreate && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="size-4" />
            Log feedback
          </Button>
        )}
      </div>

      {isError ? (
        <ErrorState title="Could not load feedback" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRows}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No feedback matches these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters."
              : "Feedback captured from review requests or logged manually will appear here."
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

      <CreateFeedbackModal open={showCreate} onOpenChange={setShowCreate} />
      <FeedbackDetailDrawer
        feedbackId={selectedFeedbackId}
        onOpenChange={(open) => !open && setSelectedFeedbackId(undefined)}
      />
    </div>
  );
}
