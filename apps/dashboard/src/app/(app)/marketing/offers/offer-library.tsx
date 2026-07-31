"use client";

import { useMemo, useState } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Offer, OfferType } from "@rkpr/contracts";
import { Plus } from "lucide-react";
import Link from "next/link";

import { useOfferList } from "@/lib/hooks/use-offers";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { OFFER_STATUS_TONES, humanize } from "@/lib/crm-display";
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
import { CreateOfferModal } from "./create-offer-modal";

const PAGE_SIZE = 25;
const ALL = "__all";
const STATUSES = [
  "draft",
  "in_review",
  "approved",
  "active",
  "paused",
  "expired",
  "cancelled",
  "archived",
];
const OFFER_TYPES: OfferType[] = [
  "percentage_discount",
  "fixed_discount",
  "item_discount",
  "category_discount",
  "buy_x_get_y",
  "combo_price",
  "free_item",
  "delivery_fee_discount",
  "loyalty_bonus",
  "internal_credit",
  "service_recovery",
];

export function OfferLibrary() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState(ALL);
  const [offerType, setOfferType] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const canCreate = hasPermission(currentUser, "offers.manage");

  const { data, isLoading, isError, refetch } = useOfferList({
    page,
    pageSize: PAGE_SIZE,
    status: status === ALL ? undefined : status,
    offerType: offerType === ALL ? undefined : offerType,
  });

  const filteredRows = useMemo(() => {
    const rows = data?.data ?? [];
    if (!search) return rows;
    const lower = search.toLowerCase();
    return rows.filter(
      (row) =>
        row.internal_name.toLowerCase().includes(lower) ||
        row.customer_facing_name.toLowerCase().includes(lower) ||
        row.offer_code.toLowerCase().includes(lower),
    );
  }, [data, search]);

  const columns = useMemo<ColumnDef<Offer, unknown>[]>(
    () => [
      {
        id: "name",
        header: "Offer",
        enableSorting: false,
        cell: ({ row }) => (
          <Link href={`/marketing/offers/${row.original.id}`} className="font-medium hover:underline">
            <div className="flex flex-col">
              <span>{row.original.internal_name}</span>
              <span className="text-muted-foreground text-xs">{row.original.offer_code}</span>
            </div>
          </Link>
        ),
      },
      {
        id: "offer_type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.offer_type)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge label={humanize(row.original.status)} tone={OFFER_STATUS_TONES[row.original.status]} />
        ),
      },
      {
        id: "redemptions",
        header: "Redemptions",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.redemption_count}
            {row.original.redemption_cap ? ` / ${row.original.redemption_cap}` : ""}
          </span>
        ),
      },
      {
        id: "version",
        header: "Version",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">v{row.original.latest_version_number}</span>,
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
        title="Offers & Coupons"
        description="Discount offers, eligibility rules, coupons, and redemption tracking."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New offer
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
        hasActiveFilters={!!search || status !== ALL || offerType !== ALL}
        onReset={() => {
          setSearchInput("");
          setStatus(ALL);
          setOfferType(ALL);
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
              value={offerType}
              onValueChange={(value) => {
                setOfferType(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-48" aria-label="Filter by type">
                <SelectValue placeholder="Offer type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All types</SelectItem>
                {OFFER_TYPES.map((t) => (
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
        <ErrorState title="Could not load offers" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={filteredRows}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No offers match these filters"
          emptyDescription={
            search || status !== ALL || offerType !== ALL
              ? "Try clearing the filters."
              : "Create the first offer to start running promotions."
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

      <CreateOfferModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
