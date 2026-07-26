"use client";

import { useState } from "react";
import type { Order, OrderStatus } from "@rkpr/contracts";

import { useTransitionOrder } from "@/lib/hooks/use-orders";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** Mirrors app/orders/states.py::ALLOWED_TRANSITIONS so staff are only
 * offered moves the backend will accept. The backend re-validates every
 * transition regardless — this is usability, not enforcement
 * (ARCHITECTURE_AND_TECH_STACK.md section 6.9). */
export const ALLOWED_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  draft: ["pending_confirmation"],
  pending_confirmation: ["confirmed", "cancelled"],
  confirmed: ["preparing"],
  preparing: ["ready", "cancelled"],
  ready: ["completed", "cancelled"],
  completed: [],
  cancelled: [],
};

/** Cancel and complete are the two terminal-ish actions this phase's own
 * instruction requires a confirmation dialog for; the routine happy-path
 * progressions (draft -> ... -> ready) apply immediately. */
const CONFIRM_REQUIRED: OrderStatus[] = ["cancelled", "completed"];

export function OrderStatusControl({ order }: { order: Order }) {
  const transitionOrder = useTransitionOrder(order.id);
  const [reason, setReason] = useState("");
  const [pendingTarget, setPendingTarget] = useState<OrderStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const available = ALLOWED_TRANSITIONS[order.status];

  if (available.length === 0) {
    return (
      <SectionCard title="Order status">
        <p className="text-muted-foreground text-sm">
          This order is {humanize(order.status).toLowerCase()} — it has reached the end of the
          workflow and cannot be moved further.
        </p>
      </SectionCard>
    );
  }

  async function applyTransition(target: OrderStatus) {
    setError(null);
    try {
      await transitionOrder.mutateAsync({ newStatus: target, reason: reason.trim() || undefined });
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The status could not be changed.");
    }
  }

  return (
    <SectionCard
      title="Order status"
      description={`Currently ${humanize(order.status).toLowerCase()}. Only valid next steps are shown.`}
    >
      <div className="flex flex-wrap items-end gap-3">
        <FormField label="Note (optional)" htmlFor="order-transition-reason" className="min-w-56 flex-1">
          <Input
            id="order-transition-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why is it moving?"
          />
        </FormField>

        {available.map((target) => (
          <Button
            key={target}
            variant={target === "cancelled" ? "destructive" : "default"}
            disabled={transitionOrder.isPending}
            onClick={() =>
              CONFIRM_REQUIRED.includes(target) ? setPendingTarget(target) : void applyTransition(target)
            }
          >
            {humanize(target)}
          </Button>
        ))}
      </div>

      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}

      <ConfirmDialog
        open={pendingTarget !== null}
        onOpenChange={(open) => !open && setPendingTarget(null)}
        variant={pendingTarget === "cancelled" ? "danger" : "confirm"}
        title={
          pendingTarget === "cancelled"
            ? "Cancel this order?"
            : "Mark this order completed?"
        }
        description={
          pendingTarget === "cancelled"
            ? "This is final — a cancelled order cannot be reopened."
            : "This is final — a completed order becomes read-only."
        }
        confirmLabel={pendingTarget === "cancelled" ? "Cancel order" : "Mark completed"}
        onConfirm={async () => {
          if (pendingTarget) await applyTransition(pendingTarget);
        }}
      />
    </SectionCard>
  );
}
