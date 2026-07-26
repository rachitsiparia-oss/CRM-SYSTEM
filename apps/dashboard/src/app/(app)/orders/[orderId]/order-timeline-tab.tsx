"use client";

import { History } from "lucide-react";

import { useOrderTimeline } from "@/lib/hooks/use-orders";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";

export function OrderTimelineTab({ orderId }: { orderId: string }) {
  const { data: timeline, isLoading } = useOrderTimeline(orderId);

  return (
    <SectionCard title="Timeline" description="Every automatically-recorded event for this order.">
      {isLoading ? (
        <CardSkeleton />
      ) : !timeline || timeline.length === 0 ? (
        <EmptyState icon={History} title="No activity yet" description="Timeline events will appear here as the order progresses." />
      ) : (
        <ol className="flex flex-col gap-4">
          {timeline.map((entry) => (
            <li key={entry.id} className="flex gap-3">
              <div className="bg-muted mt-1 size-2 shrink-0 rounded-full" />
              <div>
                <p className="text-sm font-medium">{humanize(entry.event_type)}</p>
                <p className="text-muted-foreground text-sm">{entry.summary}</p>
                <p className="text-muted-foreground text-xs">{formatDateTime(entry.occurred_at)}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </SectionCard>
  );
}
