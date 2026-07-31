"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Segment } from "@rkpr/contracts";
import { Plus } from "lucide-react";
import Link from "next/link";

import { useSegmentList } from "@/lib/hooks/use-segments";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { SEGMENT_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { FilterBar } from "@/components/filter-bar";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CreateSegmentModal } from "./create-segment-modal";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = ["draft", "active", "archived"];
const SEGMENT_TYPES = ["dynamic", "static"];

export function SegmentLibrary() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState(ALL);
  const [segmentType, setSegmentType] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const canCreate = hasPermission(currentUser, "segments.manage");

  const { data, isLoading, isError, refetch } = useSegmentList({
    page,
    pageSize: PAGE_SIZE,
    status: status === ALL ? undefined : status,
    segmentType: segmentType === ALL ? undefined : segmentType,
  });

  const filteredRows = useMemo(() => {
    const rows = data?.data ?? [];
    if (!search) return rows;
    const lower = search.toLowerCase();
    return rows.filter(
      (row) => row.name.toLowerCase().includes(lower) || row.code.toLowerCase().includes(lower),
    );
  }, [data, search]);

  const columns = useMemo<ColumnDef<Segment, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Segment",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/marketing/segments/${row.original.id}`}
            className="font-medium hover:underline"
          >
            <div className="flex flex-col">
              <span>{row.original.name}</span>
              <span className="text-muted-foreground text-xs">{row.original.code}</span>
            </div>
          </Link>
        ),
      },
      {
        id: "segment_type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => (
          <Badge variant="secondary" className="capitalize">
            {row.original.segment_type}
          </Badge>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={SEGMENT_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "count",
        header: "Members",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{row.original.last_computed_count ?? "—"}</span>
        ),
      },
      {
        id: "last_refreshed_at",
        header: "Last refreshed",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatDateTime(row.original.last_refreshed_at)}</span>
        ),
      },
    ],
    [],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Segments"
        description="Dynamic (rule-evaluated) and static (manually curated) customer segments."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New segment
            </Button>
          ) : null
        }
      />

      <FilterBar
        search={searchInput}
        onSearchChange={setSearchInput}
        searchPlaceholder="Search name or code…"
        hasActiveFilters={!!search || status !== ALL || segmentType !== ALL}
        onReset={() => {
          setSearchInput("");
          setStatus(ALL);
          setSegmentType(ALL);
          setPage(1);
        }}
        filters={
          <>
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
              value={segmentType}
              onValueChange={(value) => {
                setSegmentType(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-40" aria-label="Filter by type">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All types</SelectItem>
                {SEGMENT_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {humanize(t)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        }
      />

      {isError ? (
        <ErrorState title="Could not load segments" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRows}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No segments match these filters"
          emptyDescription={
            search || status !== ALL || segmentType !== ALL
              ? "Try clearing the filters."
              : "Create the first segment to start targeting customers."
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

      <CreateSegmentModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
