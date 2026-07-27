"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { useReservationDetail } from "@/lib/hooks/use-reservations";
import { formatDate, formatDateTime, formatTime, humanize, RESERVATION_STATUS_TONES } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ReservationStatusControl } from "./reservation-status-control";
import { ReservationAssignControl } from "./reservation-assign-control";
import { ReservationTimelineTab } from "./reservation-timeline-tab";
import { ReservationNotesTab } from "./reservation-notes-tab";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value}</dd>
    </div>
  );
}

export function ReservationDetail({ reservationId }: { reservationId: string }) {
  const { data: reservation, isLoading, isError, refetch } = useReservationDetail(reservationId);

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !reservation) {
    return (
      <div className="flex-1 p-6">
        <ErrorState
          variant="404"
          title="Reservation not found"
          description="This reservation may not exist, or you may not have access to it."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/reservations/list"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Reservations
        </Link>
      </div>

      <PageHeader
        title={reservation.guest_name}
        description={`${reservation.reservation_number} · ${humanize(reservation.source)} · ${formatDate(reservation.reservation_date)} at ${formatTime(reservation.start_time)}`}
        actions={
          <StatusBadge
            label={humanize(reservation.status)}
            tone={RESERVATION_STATUS_TONES[reservation.status]}
          />
        }
      />

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="notes">Notes</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 flex flex-col gap-4">
          <SectionCard title="Reservation details">
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <Field label="Party size" value={String(reservation.party_size)} />
              <Field label="Phone" value={reservation.phone_e164 ?? "—"} />
              <Field label="Email" value={reservation.email ?? "—"} />
              <Field
                label="Date & time"
                value={`${formatDate(reservation.reservation_date)} · ${formatTime(reservation.start_time)}${
                  reservation.end_time ? ` – ${formatTime(reservation.end_time)}` : ""
                }`}
              />
              <Field label="Walk-in" value={reservation.is_walk_in ? "Yes" : "No"} />
              <Field
                label="Deposit"
                value={
                  reservation.deposit_required
                    ? `Required${reservation.deposit_amount_minor ? ` (₹${(reservation.deposit_amount_minor / 100).toFixed(2)})` : ""}`
                    : "Not required"
                }
              />
              <Field label="Special requests" value={reservation.special_requests ?? "—"} />
              {reservation.rejection_reason && (
                <Field label="Rejection reason" value={reservation.rejection_reason} />
              )}
              {reservation.cancellation_reason && (
                <Field label="Cancellation reason" value={reservation.cancellation_reason} />
              )}
              <Field label="Version" value={String(reservation.version)} />
              <Field label="Created" value={formatDateTime(reservation.created_at)} />
              <Field label="Last updated" value={formatDateTime(reservation.updated_at)} />
            </dl>
          </SectionCard>

          <ReservationStatusControl reservation={reservation} />
          <ReservationAssignControl reservation={reservation} />
        </TabsContent>

        <TabsContent value="timeline" className="mt-4">
          <ReservationTimelineTab reservationId={reservationId} />
        </TabsContent>

        <TabsContent value="notes" className="mt-4">
          <ReservationNotesTab reservationId={reservationId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
