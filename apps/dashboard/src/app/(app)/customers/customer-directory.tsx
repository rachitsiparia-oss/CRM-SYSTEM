"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { CustomerListItem, CustomerStatus } from "@rkpr/contracts";
import { UserPlus } from "lucide-react";

import { useCustomerList } from "@/lib/hooks/use-customers";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { CUSTOMER_STATUS_TONES, formatMinorUnits, humanize } from "@/lib/crm-display";
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
import { CustomerCreateModal } from "./customer-create-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

const STATUS_OPTIONS: CustomerStatus[] = [
  "active",
  "inactive",
  "blacklisted",
  "archived",
  "merged",
];
const SEGMENT_OPTIONS = [
  "new",
  "repeat",
  "loyal",
  "vip",
  "at_risk",
  "dormant",
  "high_aov",
  "family",
  "corporate",
  "college_group",
  "delivery_first",
  "dine_in_first",
  "discount_sensitive",
  "complaint_recovery",
];

const columns: ColumnDef<CustomerListItem, unknown>[] = [
  {
    id: "display_name",
    header: "Customer",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex flex-col">
        <Link href={`/customers/${row.original.id}`} className="font-medium hover:underline">
          {row.original.display_name}
        </Link>
        <span className="text-muted-foreground text-xs">{row.original.customer_number}</span>
      </div>
    ),
  },
  {
    id: "contact",
    header: "Contact",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex flex-col text-sm">
        <span>{row.original.primary_phone_e164 ?? "—"}</span>
        <span className="text-muted-foreground text-xs">{row.original.primary_email ?? "—"}</span>
      </div>
    ),
  },
  {
    id: "customer_status",
    header: "Status",
    enableSorting: false,
    cell: ({ row }) => (
      <StatusBadge
        label={humanize(row.original.customer_status)}
        tone={CUSTOMER_STATUS_TONES[row.original.customer_status]}
      />
    ),
  },
  {
    id: "customer_segment",
    header: "Segment",
    enableSorting: false,
    cell: ({ row }) => (
      <span className="text-sm">{humanize(row.original.customer_segment)}</span>
    ),
  },
  {
    id: "completed_order_count",
    header: "Orders",
    enableSorting: false,
    cell: ({ row }) => <span className="text-sm">{row.original.completed_order_count}</span>,
  },
  {
    id: "lifetime_value_minor",
    header: "Lifetime value",
    enableSorting: false,
    cell: ({ row }) => (
      <span className="text-sm">{formatMinorUnits(row.original.lifetime_value_minor)}</span>
    ),
  },
];

export function CustomerDirectory() {
  const { data: currentUser } = useCurrentUser();
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [customerStatus, setCustomerStatus] = useState(ALL);
  const [customerSegment, setCustomerSegment] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);

  const { data, isLoading, isError, refetch } = useCustomerList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    customerStatus: customerStatus === ALL ? undefined : customerStatus,
    customerSegment: customerSegment === ALL ? undefined : customerSegment,
  });

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const canCreate = hasPermission(currentUser, "customers.create");
  const hasActiveFilters = !!search || customerStatus !== ALL || customerSegment !== ALL;

  function resetFilters() {
    setSearchInput("");
    setCustomerStatus(ALL);
    setCustomerSegment(ALL);
    setPage(1);
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Customers"
        description="Every guest RKPR has served or spoken to, with their profile, preferences, and history."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <UserPlus className="size-4" />
              New customer
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
        searchPlaceholder="Search name, number, phone, or email…"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={
          <>
            <Select
              value={customerStatus}
              onValueChange={(value) => {
                setCustomerStatus(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-40" aria-label="Filter by status">
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
              value={customerSegment}
              onValueChange={(value) => {
                setCustomerSegment(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44" aria-label="Filter by segment">
                <SelectValue placeholder="Segment" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All segments</SelectItem>
                {SEGMENT_OPTIONS.map((segment) => (
                  <SelectItem key={segment} value={segment}>
                    {humanize(segment)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        }
      />

      {isError ? (
        <ErrorState
          title="Could not load customers"
          description="The customer list could not be loaded right now."
          onRetry={() => void refetch()}
        />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No customers match these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters, or search for a different name."
              : "Create the first customer to get started."
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

      <CustomerCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
