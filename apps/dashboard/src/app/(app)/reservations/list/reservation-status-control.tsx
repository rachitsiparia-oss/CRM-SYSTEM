"use client";

import { useState } from "react";
import type { Reservation, ReservationStatus } from "@rkpr/contracts";

import { useDecideReservationApproval, useTransitionReservation } from "@/lib/hooks/use-reservations";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

/** Mirrors app.reservations.states.ALLOWED_TRANSITIONS so staff are only
 * offered moves the backend will accept — the backend re-validates every
 * transition regardless (ARCHITECTURE_AND_TECH_STACK.md section 6.9).
 * `approved`/`rejected` are deliberately excluded here: those two only ever
 * happen through the dedicated approval decision below, which runs the
 * capacity/hours/conflict checks PROJECT_PLAN.md section 11.2 requires. */
const ALLOWED_TRANSITIONS: Record<ReservationStatus, ReservationStatus[]> = {
  requested: ["pending_review", "cancelled_by_customer", "expired"],
  pending_review: [
    "needs_clarification",
    "cancelled_by_customer",
    "cancelled_by_restaurant",
    "expired",
  ],
  needs_clarification: [
    "pending_review",
    "cancelled_by_customer",
    "cancelled_by_restaurant",
    "expired",
  ],
  approved: ["confirmation_sending", "cancelled_by_customer", "cancelled_by_restaurant"],
  rejected: [],
  confirmation_sending: ["confirmed", "cancelled_by_customer", "cancelled_by_restaurant"],
  confirmed: [
    "reminder_scheduled",
    "arrived",
    "no_show",
    "cancelled_by_customer",
    "cancelled_by_restaurant",
  ],
  reminder_scheduled: ["arrived", "no_show", "cancelled_by_customer", "cancelled_by_restaurant"],
  arrived: ["seated", "cancelled_by_restaurant"],
  seated: ["completed"],
  completed: [],
  no_show: [],
  cancelled_by_customer: [],
  cancelled_by_restaurant: [],
  expired: [],
};

const DESTRUCTIVE: ReservationStatus[] = [
  "cancelled_by_customer",
  "cancelled_by_restaurant",
  "no_show",
  "expired",
];
const CONFIRM_REQUIRED: ReservationStatus[] = [...DESTRUCTIVE, "completed"];
const AWAITING_APPROVAL: ReservationStatus[] = ["pending_review", "needs_clarification"];

export function ReservationStatusControl({ reservation }: { reservation: Reservation }) {
  const transition = useTransitionReservation(reservation.id);
  const decideApproval = useDecideReservationApproval(reservation.id);
  const [reason, setReason] = useState("");
  const [pendingTarget, setPendingTarget] = useState<ReservationStatus | null>(null);
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const available = ALLOWED_TRANSITIONS[reservation.status];
  const awaitingApproval = AWAITING_APPROVAL.includes(reservation.status);

  if (available.length === 0 && !awaitingApproval) {
    return (
      <SectionCard title="Reservation status">
        <p className="text-muted-foreground text-sm">
          This reservation is {humanize(reservation.status).toLowerCase()} — it has reached the
          end of the workflow and cannot be moved further.
        </p>
      </SectionCard>
    );
  }

  async function applyTransition(target: ReservationStatus) {
    setError(null);
    try {
      await transition.mutateAsync({ newStatus: target, reason: reason.trim() || undefined });
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The status could not be changed.");
    }
  }

  async function approve() {
    setError(null);
    try {
      await decideApproval.mutateAsync({ approve: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "This reservation could not be approved.");
    }
  }

  async function reject() {
    setError(null);
    try {
      await decideApproval.mutateAsync({ approve: false, reason: rejectReason.trim() });
      setShowReject(false);
      setRejectReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "This reservation could not be rejected.");
    }
  }

  return (
    <SectionCard
      title="Reservation status"
      description={`Currently ${humanize(reservation.status).toLowerCase()}. Only valid next steps are shown.`}
    >
      {awaitingApproval && !showReject && (
        <div className="mb-3 flex flex-wrap gap-3">
          <Button disabled={decideApproval.isPending} onClick={() => void approve()}>
            Approve
          </Button>
          <Button
            variant="destructive"
            disabled={decideApproval.isPending}
            onClick={() => setShowReject(true)}
          >
            Reject
          </Button>
        </div>
      )}

      {awaitingApproval && showReject && (
        <div className="mb-3 flex flex-col gap-3 rounded-md border p-3">
          <FormField label="Rejection reason" htmlFor="reservation-reject-reason" required>
            <Textarea
              id="reservation-reject-reason"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
            />
          </FormField>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setShowReject(false);
                setRejectReason("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!rejectReason.trim() || decideApproval.isPending}
              onClick={() => void reject()}
            >
              {decideApproval.isPending ? "Rejecting…" : "Reject reservation"}
            </Button>
          </div>
        </div>
      )}

      {available.length > 0 && (
        <div className="flex flex-wrap items-end gap-3">
          <FormField
            label="Note (optional)"
            htmlFor="reservation-transition-reason"
            className="min-w-56 flex-1"
          >
            <Input
              id="reservation-transition-reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Why is it moving?"
            />
          </FormField>

          {available.map((target) => (
            <Button
              key={target}
              variant={DESTRUCTIVE.includes(target) ? "destructive" : "default"}
              disabled={transition.isPending}
              onClick={() =>
                CONFIRM_REQUIRED.includes(target)
                  ? setPendingTarget(target)
                  : void applyTransition(target)
              }
            >
              {humanize(target)}
            </Button>
          ))}
        </div>
      )}

      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}

      <ConfirmDialog
        open={pendingTarget !== null}
        onOpenChange={(open) => !open && setPendingTarget(null)}
        variant={pendingTarget && DESTRUCTIVE.includes(pendingTarget) ? "danger" : "confirm"}
        title={pendingTarget ? `${humanize(pendingTarget)} this reservation?` : ""}
        description="This is final for this reservation's lifecycle."
        confirmLabel={pendingTarget ? humanize(pendingTarget) : "Confirm"}
        onConfirm={async () => {
          if (pendingTarget) await applyTransition(pendingTarget);
        }}
      />
    </SectionCard>
  );
}
