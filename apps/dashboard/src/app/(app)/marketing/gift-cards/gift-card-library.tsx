"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { GiftCard } from "@rkpr/contracts";
import { CreditCard, Plus } from "lucide-react";
import Link from "next/link";

import { useGiftCardAnalytics, useGiftCardList } from "@/lib/hooks/use-gift-cards";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { GIFT_CARD_STATUS_TONES, formatDate, formatMinorUnits, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { FilterBar } from "@/components/filter-bar";
import { DataTable } from "@/components/data-table/data-table";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { IssueGiftCardModal } from "./issue-gift-card-modal";
import { RedeemGiftCardModal } from "./redeem-gift-card-modal";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = [
  "draft",
  "active",
  "partially_redeemed",
  "fully_redeemed",
  "expired",
  "suspended",
  "cancelled",
];

export function GiftCardLibrary() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [customerIdInput, setCustomerIdInput] = useState("");
  const [status, setStatus] = useState(ALL);
  const [showIssue, setShowIssue] = useState(false);
  const [showRedeem, setShowRedeem] = useState(false);

  const customerId = useDebouncedValue(customerIdInput);
  const canIssue = hasPermission(currentUser, "gift_cards.issue");
  const canRedeem = hasPermission(currentUser, "gift_cards.manage");
  const canViewAnalytics = hasPermission(currentUser, "gift_cards.analytics.view");

  const { data, isLoading, isError, refetch } = useGiftCardList({
    page,
    pageSize: PAGE_SIZE,
    status: status === ALL ? undefined : status,
    customerId: customerId || undefined,
  });
  const { data: analytics, isLoading: analyticsLoading } = useGiftCardAnalytics();

  const columns = useMemo<ColumnDef<GiftCard, unknown>[]>(
    () => [
      {
        id: "card",
        header: "Gift card",
        enableSorting: false,
        cell: ({ row }) => (
          <Link
            href={`/marketing/gift-cards/${row.original.id}`}
            className="font-medium hover:underline"
          >
            <span className="font-mono text-sm">{row.original.masked_display}</span>
          </Link>
        ),
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={GIFT_CARD_STATUS_TONES[row.original.status]}
          />
        ),
      },
      {
        id: "balance",
        header: "Balance",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatMinorUnits(row.original.current_balance_minor)}</span>,
      },
      {
        id: "initial",
        header: "Initial amount",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatMinorUnits(row.original.initial_amount_minor)}</span>,
      },
      {
        id: "recipient",
        header: "Recipient",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.recipient_name ?? row.original.recipient_contact ?? "—"}
          </span>
        ),
      },
      {
        id: "expires_at",
        header: "Expires",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{formatDate(row.original.expires_at)}</span>,
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
        title="Gift cards"
        description="Issued gift cards, balances, and redemption history."
        actions={
          <div className="flex flex-wrap gap-2">
            {canRedeem && (
              <Button variant="outline" onClick={() => setShowRedeem(true)}>
                <CreditCard className="size-4" />
                Redeem
              </Button>
            )}
            {canIssue && (
              <Button onClick={() => setShowIssue(true)}>
                <Plus className="size-4" />
                Issue gift card
              </Button>
            )}
          </div>
        }
      />

      {canViewAnalytics && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Active cards" value={analytics?.active_cards ?? 0} loading={analyticsLoading} />
          <StatCard
            label="Outstanding liability"
            value={formatMinorUnits(analytics?.outstanding_liability_minor)}
            loading={analyticsLoading}
          />
          <StatCard
            label="Issued (30d)"
            value={formatMinorUnits(analytics?.issued_30d_minor)}
            loading={analyticsLoading}
          />
          <StatCard
            label="Redeemed (30d)"
            value={formatMinorUnits(analytics?.redeemed_30d_minor)}
            loading={analyticsLoading}
          />
        </div>
      )}

      <FilterBar
        search={customerIdInput}
        onSearchChange={(value) => {
          setCustomerIdInput(value);
          setPage(1);
        }}
        searchPlaceholder="Filter by customer ID…"
        hasActiveFilters={!!customerId || status !== ALL}
        onReset={() => {
          setCustomerIdInput("");
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
            <SelectTrigger className="w-48" aria-label="Filter by status">
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
        <ErrorState title="Could not load gift cards" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No gift cards match these filters"
          emptyDescription={
            customerId || status !== ALL
              ? "Try clearing the filters."
              : "Issue the first gift card to get started."
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

      <IssueGiftCardModal open={showIssue} onOpenChange={setShowIssue} />
      <RedeemGiftCardModal open={showRedeem} onOpenChange={setShowRedeem} />
    </div>
  );
}
