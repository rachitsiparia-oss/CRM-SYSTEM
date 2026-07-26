"use client";

import { History } from "lucide-react";

import { useCustomerTimeline } from "@/lib/hooks/use-customers";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

/** Reads the customer's audit trail — the same immutable record used for
 * compliance, not a separate display-only log (CLAUDE.md section 6.6). */
export function CustomerTimeline({ customerId }: { customerId: string }) {
  const { data: entries, isLoading } = useCustomerTimeline(customerId);

  return (
    <SectionCard
      title="Activity timeline"
      description="Every recorded change to this customer, newest first."
    >
      {isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : !entries || entries.length === 0 ? (
        <EmptyState
          icon={History}
          title="Nothing recorded yet"
          description="Profile changes, merges, and assignments will appear here."
        />
      ) : (
        <ol className="flex flex-col gap-3">
          {entries.map((entry) => (
            <li key={entry.id} className="flex gap-3 border-l-2 pl-3">
              <div className="flex flex-col">
                <span className="text-sm font-medium">{humanize(entry.action_code)}</span>
                <span className="text-muted-foreground text-xs">
                  {formatDateTime(entry.created_at)}
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </SectionCard>
  );
}
