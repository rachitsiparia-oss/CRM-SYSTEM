"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { useDiningAreas, useReservationList } from "@/lib/hooks/use-reservations";
import { RESERVATION_STATUS_TONES, formatTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function today(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());
}

function shiftDate(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export function ReservationCalendar() {
  const [selectedDate, setSelectedDate] = useState(today());
  const { data: diningAreas } = useDiningAreas();
  const { data, isLoading } = useReservationList({
    page: 1,
    pageSize: 100,
    dateFrom: selectedDate,
    dateTo: selectedDate,
  });

  const diningAreaName = useMemo(
    () => new Map((diningAreas ?? []).map((a) => [a.id, a.name])),
    [diningAreas],
  );

  const reservations = useMemo(
    () => (data?.data ?? []).slice().sort((a, b) => a.start_time.localeCompare(b.start_time)),
    [data],
  );

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Calendar"
        description="Reservations for a single day, grouped by time — the day view."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              aria-label="Previous day"
              onClick={() => setSelectedDate((d) => shiftDate(d, -1))}
            >
              <ChevronLeft className="size-4" />
            </Button>
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-40"
            />
            <Button
              variant="outline"
              size="icon"
              aria-label="Next day"
              onClick={() => setSelectedDate((d) => shiftDate(d, 1))}
            >
              <ChevronRight className="size-4" />
            </Button>
            <Button variant="outline" onClick={() => setSelectedDate(today())}>
              Today
            </Button>
          </div>
        }
      />

      <SectionCard title={`${reservations.length} reservation(s)`}>
        {isLoading ? (
          <CardSkeleton />
        ) : reservations.length === 0 ? (
          <EmptyState title="No reservations on this date" description="Nothing is booked for this day yet." />
        ) : (
          <ul className="flex flex-col gap-2">
            {reservations.map((reservation) => (
              <li key={reservation.id}>
                <Link
                  href={`/reservations/list/${reservation.id}`}
                  className="hover:border-primary flex items-center justify-between rounded-md border p-3"
                >
                  <div className="flex items-center gap-4">
                    <span className="w-20 text-sm font-medium">{formatTime(reservation.start_time)}</span>
                    <div>
                      <p className="text-sm font-medium">{reservation.guest_name}</p>
                      <p className="text-muted-foreground text-xs">
                        Party of {reservation.party_size}
                        {reservation.dining_area_id
                          ? ` · ${diningAreaName.get(reservation.dining_area_id)}`
                          : ""}
                      </p>
                    </div>
                  </div>
                  <StatusBadge
                    label={humanize(reservation.status)}
                    tone={RESERVATION_STATUS_TONES[reservation.status]}
                  />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </SectionCard>
    </div>
  );
}
