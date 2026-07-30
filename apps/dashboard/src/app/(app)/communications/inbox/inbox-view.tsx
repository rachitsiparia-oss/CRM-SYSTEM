"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { Conversation } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useInboxList, useCommunicationChannels } from "@/lib/hooks/use-communications";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  CONVERSATION_PRIORITY_TONES,
  CONVERSATION_STATUS_TONES,
  formatDateTime,
  humanize,
} from "@/lib/crm-display";
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
import { NewConversationModal } from "./new-conversation-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

const STATUS_OPTIONS = [
  "open",
  "pending",
  "waiting_on_customer",
  "waiting_on_staff",
  "snoozed",
  "resolved",
  "closed",
  "spam",
];

export function InboxView() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [conversationStatus, setConversationStatus] = useState(ALL);
  const [channelId, setChannelId] = useState(ALL);
  const [view, setView] = useState<"all" | "unassigned" | "mine">("all");
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const { data: channels } = useCommunicationChannels();

  const { data, isLoading, isError, refetch } = useInboxList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    conversationStatus: conversationStatus === ALL ? undefined : conversationStatus,
    channelId: channelId === ALL ? undefined : channelId,
    unassignedOnly: view === "unassigned",
    mineOnly: view === "mine",
  });

  const canCreate = hasPermission(currentUser, "communications.create");
  const channelName = useMemo(
    () => new Map((channels ?? []).map((c) => [c.id, c.name])),
    [channels],
  );

  const columns = useMemo<ColumnDef<Conversation, unknown>[]>(
    () => [
      {
        id: "conversation",
        header: "Conversation",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <Link
              href={`/communications/inbox/${row.original.id}`}
              className="font-medium hover:underline"
            >
              {row.original.subject ?? row.original.guest_name ?? row.original.conversation_number}
            </Link>
            <span className="text-muted-foreground text-xs">
              {row.original.conversation_number}
            </span>
          </div>
        ),
      },
      {
        id: "channel",
        header: "Channel",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{channelName.get(row.original.channel_id) ?? "—"}</span>
        ),
      },
      {
        id: "priority",
        header: "Priority",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.priority)}
            tone={CONVERSATION_PRIORITY_TONES[row.original.priority]}
          />
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={CONVERSATION_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "unread",
        header: "Unread",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{row.original.unread_count > 0 ? row.original.unread_count : "—"}</span>
        ),
      },
      {
        id: "last_activity",
        header: "Last activity",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">{formatDateTime(row.original.last_activity_at)}</span>
        ),
      },
    ],
    [channelName],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const hasActiveFilters =
    !!search || conversationStatus !== ALL || channelId !== ALL || view !== "all";

  function resetFilters() {
    setSearchInput("");
    setConversationStatus(ALL);
    setChannelId(ALL);
    setView("all");
    setPage(1);
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Unified inbox"
        description="Every customer conversation, across every channel, in one place."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New conversation
            </Button>
          ) : null
        }
      />

      <div className="flex gap-2">
        {(["all", "unassigned", "mine"] as const).map((tab) => (
          <Button
            key={tab}
            variant={view === tab ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setView(tab);
              setPage(1);
            }}
          >
            {tab === "all" ? "All" : tab === "unassigned" ? "Unassigned" : "My conversations"}
          </Button>
        ))}
      </div>

      <FilterBar
        search={searchInput}
        onSearchChange={(value) => {
          setSearchInput(value);
          setPage(1);
        }}
        searchPlaceholder="Search subject, number, guest, or phone…"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={
          <>
            <Select
              value={conversationStatus}
              onValueChange={(value) => {
                setConversationStatus(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-48" aria-label="Filter by status">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All statuses</SelectItem>
                {STATUS_OPTIONS.map((status) => (
                  <SelectItem key={status} value={status}>
                    {humanize(status)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={channelId}
              onValueChange={(value) => {
                setChannelId(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44" aria-label="Filter by channel">
                <SelectValue placeholder="Channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All channels</SelectItem>
                {(channels ?? []).map((channel) => (
                  <SelectItem key={channel.id} value={channel.id}>
                    {channel.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        }
      />

      {isError ? (
        <ErrorState title="Could not load the inbox" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No conversations match these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters, or search for something else."
              : "Start the first conversation to get going."
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

      <NewConversationModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
