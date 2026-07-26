"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { ColumnDef } from "@tanstack/react-table";
import type { OrderListItem } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useOrderList } from "@/lib/hooks/use-orders";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  formatDateTime,
  formatMinorUnits,
  humanize,
  ORDER_STATUS_TONES,
  PAYMENT_STATUS_TONES,
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

const PAGE_SIZE = 25;
const ALL = "__all";

const STATUS_OPTIONS = [
  "draft",
  "pending_confirmation",
  "confirmed",
  "preparing",
  "ready",
  "completed",
  "cancelled",
];
const SOURCE_OPTIONS = ["pos", "walk_in", "website", "whatsapp", "phone_call", "zomato", "swiggy", "manual"];
const ORDER_TYPE_OPTIONS = ["dine_in", "takeaway", "delivery"];
const PAYMENT_STATUS_OPTIONS = ["pending", "partial", "paid", "refunded", "failed"];
const SORT_OPTIONS: { value: string; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "highest_amount", label: "Highest amount" },
  { value: "lowest_amount", label: "Lowest amount" },
  { value: "completion_time", label: "Completion time" },
];

const columns: ColumnDef<OrderListItem, unknown>[] = [
  {
    id: "order_number",
    header: "Order",
    enableSorting: false,
    cell: ({ row }) => (
      <Link href={`/orders/${row.original.id}`} className="font-medium hover:underline">
        {row.original.order_number}
      </Link>
    ),
  },
  {
    id: "status",
    header: "Status",
    enableSorting: false,
    cell: ({ row }) => (
      <StatusBadge label={humanize(row.original.status)} tone={ORDER_STATUS_TONES[row.original.status]} />
    ),
  },
  {
    id: "payment_status",
    header: "Payment",
    enableSorting: false,
    cell: ({ row }) => (
      <StatusBadge
        label={humanize(row.original.payment_status)}
        tone={PAYMENT_STATUS_TONES[row.original.payment_status]}
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
    id: "order_type",
    header: "Type",
    enableSorting: false,
    cell: ({ row }) => <span className="text-sm">{humanize(row.original.order_type)}</span>,
  },
  {
    id: "grand_total_minor",
    header: "Total",
    enableSorting: false,
    cell: ({ row }) => (
      <span className="text-sm font-medium">{formatMinorUnits(row.original.grand_total_minor)}</span>
    ),
  },
  {
    id: "created_at",
    header: "Created",
    enableSorting: false,
    cell: ({ row }) => <span className="text-sm">{formatDateTime(row.original.created_at)}</span>,
  },
];

export function OrderDirectory() {
  const router = useRouter();
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [orderStatus, setOrderStatus] = useState(ALL);
  const [source, setSource] = useState(ALL);
  const [orderType, setOrderType] = useState(ALL);
  const [paymentStatus, setPaymentStatus] = useState(ALL);
  const [sort, setSort] = useState("newest");

  const search = useDebouncedValue(searchInput);

  const { data, isLoading, isError, refetch } = useOrderList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    orderStatus: orderStatus === ALL ? undefined : orderStatus,
    source: source === ALL ? undefined : source,
    orderType: orderType === ALL ? undefined : orderType,
    paymentStatus: paymentStatus === ALL ? undefined : paymentStatus,
    sort,
  });

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const canCreate = hasPermission(currentUser, "orders.create");
  const hasActiveFilters =
    !!search || orderStatus !== ALL || source !== ALL || orderType !== ALL || paymentStatus !== ALL;

  function resetFilters() {
    setSearchInput("");
    setOrderStatus(ALL);
    setSource(ALL);
    setOrderType(ALL);
    setPaymentStatus(ALL);
    setPage(1);
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Orders"
        description="Every order across dine-in, takeaway, and delivery — from every source."
        actions={
          canCreate ? (
            <Button onClick={() => router.push("/orders/new")}>
              <Plus className="size-4" />
              New order
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
        searchPlaceholder="Search order number…"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={
          <>
            <Select
              value={orderStatus}
              onValueChange={(value) => {
                setOrderStatus(value);
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
              <SelectTrigger className="w-40" aria-label="Filter by source">
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
              value={orderType}
              onValueChange={(value) => {
                setOrderType(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-36" aria-label="Filter by order type">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All types</SelectItem>
                {ORDER_TYPE_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {humanize(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={paymentStatus}
              onValueChange={(value) => {
                setPaymentStatus(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-40" aria-label="Filter by payment status">
                <SelectValue placeholder="Payment" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All payment statuses</SelectItem>
                {PAYMENT_STATUS_OPTIONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {humanize(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={sort} onValueChange={setSort}>
              <SelectTrigger className="w-40" aria-label="Sort orders">
                <SelectValue placeholder="Sort" />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        }
      />

      {isError ? (
        <ErrorState
          title="Could not load orders"
          description="The order list could not be loaded right now."
          onRetry={() => void refetch()}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No orders match these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters, or search for a different order."
              : "Create the first order to get started."
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
    </div>
  );
}
