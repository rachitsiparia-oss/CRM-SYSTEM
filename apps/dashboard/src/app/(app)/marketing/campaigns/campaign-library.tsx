"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Campaign } from "@rkpr/contracts";
import { Plus } from "lucide-react";
import Link from "next/link";

import { useCampaignList } from "@/lib/hooks/use-campaigns";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { CAMPAIGN_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
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
import { CreateCampaignModal } from "./create-campaign-modal";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = [
  "draft",
  "ready",
  "scheduled",
  "running",
  "paused",
  "completed",
  "cancelled",
  "failed",
  "archived",
];

export function CampaignLibrary() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const canCreate = hasPermission(currentUser, "campaigns.manage");

  const { data, isLoading, isError, refetch } = useCampaignList({
    page,
    pageSize: PAGE_SIZE,
    status: status === ALL ? undefined : status,
  });

  const filteredRows = useMemo(() => {
    const rows = data?.data ?? [];
    if (!search) return rows;
    const lower = search.toLowerCase();
    return rows.filter(
      (row) => row.name.toLowerCase().includes(lower) || row.code.toLowerCase().includes(lower),
    );
  }, [data, search]);

  const columns = useMemo<ColumnDef<Campaign, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Campaign",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/marketing/campaigns/${row.original.id}`}
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
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge label={humanize(row.original.status)} tone={CAMPAIGN_STATUS_TONES[row.original.status]} />
        ),
      },
      {
        id: "channels",
        header: "Channels",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{Object.keys(row.original.channel_templates).join(", ") || "—"}</span>
        ),
      },
      {
        id: "estimated_size",
        header: "Est. audience",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.estimated_size ?? "—"}</span>,
      },
      {
        id: "scheduled_at",
        header: "Scheduled",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.scheduled_at)}</span>,
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
        title="Campaigns"
        description="Segment-targeted WhatsApp, email, and SMS campaigns."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New campaign
            </Button>
          ) : null
        }
      />

      <FilterBar
        search={searchInput}
        onSearchChange={(value) => {
          setSearchInput(value);
          setPage(1);
        }}
        searchPlaceholder="Search name or code…"
        hasActiveFilters={!!search || status !== ALL}
        onReset={() => {
          setSearchInput("");
          setStatus(ALL);
          setPage(1);
        }}
        filters={
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
        }
      />

      {isError ? (
        <ErrorState title="Could not load campaigns" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRows}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No campaigns match these filters"
          emptyDescription={
            search || status !== ALL
              ? "Try clearing the filters."
              : "Create the first campaign to start reaching customers."
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

      <CreateCampaignModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
