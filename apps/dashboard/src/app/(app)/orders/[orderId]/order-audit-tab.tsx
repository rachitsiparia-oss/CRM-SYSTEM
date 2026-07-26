"use client";

import { ShieldCheck } from "lucide-react";

import { useOrderStatusHistory } from "@/lib/hooks/use-orders";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";

/** The order's own audit surface for this phase — the append-only status
 * transition ledger (who changed what status, when, and why). Broader
 * cross-entity audit trail browsing belongs to the system-wide audit.view
 * permission and screen, not duplicated per-order here. */
export function OrderAuditTab({ orderId }: { orderId: string }) {
  const { data: history, isLoading } = useOrderStatusHistory(orderId);

  return (
    <SectionCard title="Status audit trail" description="Every status change, with who made it and why.">
      {isLoading ? (
        <CardSkeleton />
      ) : !history || history.length === 0 ? (
        <EmptyState icon={ShieldCheck} title="No status changes yet" description="Status changes will appear here." />
      ) : (
        <ul className="flex flex-col gap-3">
          {history.map((entry) => (
            <li key={entry.id} className="rounded-md border p-3 text-sm">
              <p>
                {entry.previous_status ? humanize(entry.previous_status) : "Created"} →{" "}
                <span className="font-medium">{humanize(entry.new_status)}</span>
              </p>
              {entry.reason && <p className="text-muted-foreground text-xs">Reason: {entry.reason}</p>}
              <p className="text-muted-foreground text-xs">{formatDateTime(entry.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}
