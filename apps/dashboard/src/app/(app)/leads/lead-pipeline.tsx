"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { LeadListItem } from "@rkpr/contracts";
import { AlertTriangle, Plus } from "lucide-react";

import { useLeadList } from "@/lib/hooks/use-leads";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  formatDate,
  formatMinorUnits,
  humanize,
  isOverdue,
  LEAD_PRIORITY_TONES,
  LEAD_STATUS_TONES,
} from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { FilterBar } from "@/components/filter-bar";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LeadCreateModal } from "./lead-create-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

const STATUS_OPTIONS = [
  "new",
  "contacted",
  "qualified",
  "interested",
  "follow_up_scheduled",
  "proposal_shared",
  "negotiating",
  "won",
  "lost",
  "closed",
];
const SOURCE_OPTIONS = [
  "website",
  "phone",
  "walk_in",
  "whatsapp",
  "zomato_import",
  "swiggy_import",
  "meta_campaign",
  "google_campaign",
  "referral",
  "corporate_outreach",
  "event_enquiry",
  "offline_qr",
];
const PRIORITY_OPTIONS = ["low", "normal", "high", "urgent"];

const columns: ColumnDef<LeadListItem, unknown>[] = [
  {
    id: "display_name",
    header: "Lead",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex flex-col">
        <Link href={`/leads/${row.original.id}`} className="font-medium hover:underline">
          {row.original.display_name}
        </Link>
        <span className="text-muted-foreground text-xs">
          {row.original.lead_number}
          {row.original.organization_name ? ` · ${row.original.organization_name}` : ""}
        </span>
      </div>
    ),
  },
  {
    id: "status",
    header: "Status",
    enableSorting: false,
    cell: ({ row }) => (
      <StatusBadge
        label={humanize(row.original.status)}
        tone={LEAD_STATUS_TONES[row.original.status]}
      />
    ),
  },
  {
    id: "priority",
    header: "Priority",
    enableSorting: false,
    cell: ({ row }) => (
      <StatusBadge
        label={humanize(row.original.priority)}
        tone={LEAD_PRIORITY_TONES[row.original.priority]}
      />
    ),
  },
  {
    id: "source",
    header: "Source",
    enableSorting: false,
    cell: ({ row }) => <span className="text-sm">{humanize(row.original.source)}</span>,
  },
  {
    id: "estimated_value_minor",
    header: "Est. value",
    enableSorting: false,
    cell: ({ row }) => (
      <span className="text-sm">{formatMinorUnits(row.original.estimated_value_minor)}</span>
    ),
  },
  {
    id: "next_follow_up_at",
    header: "Next follow-up",
    enableSorting: false,
    cell: ({ row }) => {
      const value = row.original.next_follow_up_at;
      const overdue = isOverdue(value) && !["won", "lost", "closed"].includes(row.original.status);
      return (
        <span
          className={
            overdue ? "text-destructive flex items-center gap-1 text-sm font-medium" : "text-sm"
          }
        >
          {overdue && <AlertTriangle className="size-3.5" aria-hidden="true" />}
          {formatDate(value)}
          {overdue && <span className="sr-only">(overdue)</span>}
        </span>
      );
    },
  },
  {
    id: "assigned_staff_id",
    header: "Assigned",
    enableSorting: false,
    cell: ({ row }) =>
      row.original.assigned_staff_id ? (
        <span className="text-sm">Assigned</span>
      ) : (
        <span className="text-muted-foreground text-sm">Unassigned</span>
      ),
  },
];

export function LeadPipeline() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [leadStatus, setLeadStatus] = useState(ALL);
  const [source, setSource] = useState(ALL);
  const [priority, setPriority] = useState(ALL);
  const [unassigned, setUnassigned] = useState(false);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);

  const { data, isLoading, isError, refetch } = useLeadList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    leadStatus: leadStatus === ALL ? undefined : leadStatus,
    source: source === ALL ? undefined : source,
    priority: priority === ALL ? undefined : priority,
    unassigned,
    overdueFollowUp: overdueOnly,
  });

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const canCreate = hasPermission(currentUser, "leads.create");
  const hasActiveFilters =
    !!search ||
    leadStatus !== ALL ||
    source !== ALL ||
    priority !== ALL ||
    unassigned ||
    overdueOnly;

  function resetFilters() {
    setSearchInput("");
    setLeadStatus(ALL);
    setSource(ALL);
    setPriority(ALL);
    setUnassigned(false);
    setOverdueOnly(false);
    setPage(1);
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Leads"
        description="Enquiries from the website, delivery platforms, campaigns, and walk-ins — from first contact through conversion."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New lead
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
        searchPlaceholder="Search name, number, organization, phone, or email…"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={
          <>
            <Select
              value={leadStatus}
              onValueChange={(value) => {
                setLeadStatus(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44" aria-label="Filter by status">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All statuses</SelectItem>
                {STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {humanize(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={source}
              onValueChange={(value) => {
                setSource(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44" aria-label="Filter by source">
                <SelectValue placeholder="Source" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All sources</SelectItem>
                {SOURCE_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {humanize(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={priority}
              onValueChange={(value) => {
                setPriority(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-36" aria-label="Filter by priority">
                <SelectValue placeholder="Priority" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All priorities</SelectItem>
                {PRIORITY_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {humanize(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={unassigned}
                onCheckedChange={(checked) => {
                  setUnassigned(checked === true);
                  setPage(1);
                }}
              />
              Unassigned only
            </label>

            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={overdueOnly}
                onCheckedChange={(checked) => {
                  setOverdueOnly(checked === true);
                  setPage(1);
                }}
              />
              Overdue follow-up
            </label>
          </>
        }
      />

      {isError ? (
        <ErrorState
          title="Could not load leads"
          description="The lead pipeline could not be loaded right now."
          onRetry={() => void refetch()}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No leads match these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters, or search for a different enquiry."
              : "Create the first lead to start tracking enquiries."
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

      <LeadCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
