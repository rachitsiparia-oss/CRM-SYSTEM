"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { ColumnDef } from "@tanstack/react-table";
import type { Reservation } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useReservationList, useDiningAreas } from "@/lib/hooks/use-reservations";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { RESERVATION_STATUS_TONES, formatDate, formatTime, humanize } from "@/lib/crm-display";
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
import { ReservationCreateModal } from "./reservation-create-modal";

const PAGE_SIZE = 25;
const ALL = "__all";

const STATUS_OPTIONS = [
  "requested",
  "pending_review",
  "needs_clarification",
  "approved",
  "rejected",
  "confirmed",
  "arrived",
  "seated",
  "completed",
  "no_show",
  "cancelled_by_customer",
  "cancelled_by_restaurant",
  "expired",
];

export function ReservationDirectory() {
  const { data: currentUser } = useCurrentUser();

  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [reservationStatus, setReservationStatus] = useState(ALL);
  const [diningAreaId, setDiningAreaId] = useState(ALL);
  const [showCreate, setShowCreate] = useState(false);

  const search = useDebouncedValue(searchInput);
  const { data: diningAreas } = useDiningAreas();

  const { data, isLoading, isError, refetch } = useReservationList({
    page,
    pageSize: PAGE_SIZE,
    search: search || undefined,
    reservationStatus: reservationStatus === ALL ? undefined : reservationStatus,
    diningAreaId: diningAreaId === ALL ? undefined : diningAreaId,
  });

  const canCreate = hasPermission(currentUser, "reservations.create");
  const diningAreaName = useMemo(
    () => new Map((diningAreas ?? []).map((a) => [a.id, a.name])),
    [diningAreas],
  );

  const columns = useMemo<ColumnDef<Reservation, unknown>[]>(
    () => [
      {
        id: "guest_name",
        header: "Guest",
        enableSorting: false,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <Link
              href={`/reservations/list/${row.original.id}`}
              className="font-medium hover:underline"
            >
              {row.original.guest_name}
            </Link>
            <span className="text-muted-foreground text-xs">{row.original.reservation_number}</span>
          </div>
        ),
      },
      {
        id: "date_time",
        header: "Date & time",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {formatDate(row.original.reservation_date)} · {formatTime(row.original.start_time)}
          </span>
        ),
      },
      {
        id: "party_size",
        header: "Party size",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{row.original.party_size}</span>,
      },
      {
        id: "dining_area",
        header: "Area",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-sm">
            {row.original.dining_area_id ? diningAreaName.get(row.original.dining_area_id) : "—"}
          </span>
        ),
      },
      {
        id: "source",
        header: "Source",
        enableSorting: false,
        cell: ({ row }) => <span className="text-sm">{humanize(row.original.source)}</span>,
      },
      {
        id: "status",
        header: "Status",
        enableSorting: false,
        cell: ({ row }) => (
          <StatusBadge
            label={humanize(row.original.status)}
            tone={RESERVATION_STATUS_TONES[row.original.status]}
          />
        ),
      },
    ],
    [diningAreaName],
  );

  const pageCount = useMemo(
    () => (data ? Math.max(1, Math.ceil(data.pagination.total / PAGE_SIZE)) : 0),
    [data],
  );

  const hasActiveFilters = !!search || reservationStatus !== ALL || diningAreaId !== ALL;

  function resetFilters() {
    setSearchInput("");
    setReservationStatus(ALL);
    setDiningAreaId(ALL);
    setPage(1);
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Reservations"
        description="Every reservation request, from initial ask through completion."
        actions={
          canCreate ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              New reservation
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
        searchPlaceholder="Search guest name, number, or phone…"
        hasActiveFilters={hasActiveFilters}
        onReset={resetFilters}
        filters={
          <>
            <Select
              value={reservationStatus}
              onValueChange={(value) => {
                setReservationStatus(value);
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
              value={diningAreaId}
              onValueChange={(value) => {
                setDiningAreaId(value);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-44" aria-label="Filter by dining area">
                <SelectValue placeholder="Dining area" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All areas</SelectItem>
                {(diningAreas ?? []).map((area) => (
                  <SelectItem key={area.id} value={area.id}>
                    {area.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        }
      />

      {isError ? (
        <ErrorState title="Could not load reservations" onRetry={() => void refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={data?.data ?? []}
          getRowId={(row) => row.id}
          loading={isLoading}
          emptyTitle="No reservations match these filters"
          emptyDescription={
            hasActiveFilters
              ? "Try clearing the filters, or search for a different guest."
              : "Create the first reservation to get started."
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

      <ReservationCreateModal open={showCreate} onOpenChange={setShowCreate} />
    </div>
  );
}
