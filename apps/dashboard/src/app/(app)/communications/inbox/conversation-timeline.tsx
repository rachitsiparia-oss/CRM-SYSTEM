"use client";

import { MessagesSquare } from "lucide-react";

import { useConversationTimeline } from "@/lib/hooks/use-communications";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";

function entryLabel(entryType: string): string {
  if (entryType === "status_change") return "Status change";
  if (entryType === "assignment_change") return "Assignment change";
  return "Message";
}

export function ConversationTimeline({ conversationId }: { conversationId: string }) {
  const { data: entries, isLoading } = useConversationTimeline(conversationId);

  return (
    <SectionCard title="Timeline">
      {isLoading ? (
        <CardSkeleton />
      ) : !entries || entries.length === 0 ? (
        <EmptyState
          icon={MessagesSquare}
          title="No activity yet"
          description="Messages and status changes will appear here."
        />
      ) : (
        <ul className="flex flex-col gap-3">
          {entries.map((entry, index) => {
            const payload = entry.payload as Record<string, unknown>;
            return (
              <li key={index} className="rounded-md border p-3">
                <p className="text-muted-foreground text-xs font-medium">
                  {entryLabel(entry.entry_type)} · {formatDateTime(entry.occurred_at)}
                </p>
                {entry.entry_type === "message" && (
                  <>
                    <p className="mt-1 text-sm whitespace-pre-wrap">
                      {(payload.body_text as string | null) ?? "(no content)"}
                    </p>
                    <p className="text-muted-foreground mt-1 text-xs">
                      {humanize(payload.direction as string)} ·{" "}
                      {humanize(payload.delivery_status as string)}
                    </p>
                  </>
                )}
                {entry.entry_type === "status_change" && (
                  <p className="mt-1 text-sm">
                    {humanize((payload.previous_status as string | null) ?? "—")} →{" "}
                    {humanize(payload.new_status as string)}
                    {payload.reason ? ` — ${payload.reason as string}` : ""}
                  </p>
                )}
                {entry.entry_type === "assignment_change" && (
                  <p className="mt-1 text-sm">
                    {payload.new_assignee_id ? "Assigned" : "Unassigned"}
                    {payload.reason ? ` — ${payload.reason as string}` : ""}
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </SectionCard>
  );
}
