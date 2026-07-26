"use client";

import { useState } from "react";
import { History } from "lucide-react";

import { useAddLeadActivity, useLeadTimeline } from "@/lib/hooks/use-leads";
import { formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

/** Only the activity types staff log by hand. The rest
 * (status_change, assignment, follow_up_*, customer_conversion) are written
 * by the backend as those things happen and appear read-only in the list. */
const LOGGABLE_TYPES = ["call", "email", "whatsapp", "meeting", "proposal", "note"];

export function LeadActivity({ leadId, canEdit }: { leadId: string; canEdit: boolean }) {
  const { data: entries, isLoading } = useLeadTimeline(leadId);
  const addActivity = useAddLeadActivity(leadId);

  const [activityType, setActivityType] = useState("call");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleAdd() {
    setError(null);
    try {
      await addActivity.mutateAsync({ activity_type: activityType, summary: summary.trim() });
      setSummary("");
      setActivityType("call");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The activity could not be logged.");
    }
  }

  return (
    <SectionCard
      title="Activity"
      description="Calls, emails, meetings, and every automatic pipeline event, newest first."
    >
      <div className="flex flex-col gap-4">
        {canEdit && (
          <div className="bg-muted/40 flex flex-col gap-3 rounded-md border p-4">
            <FormField label="What happened?" htmlFor="activity-summary" required>
              <Textarea
                id="activity-summary"
                rows={2}
                value={summary}
                onChange={(event) => setSummary(event.target.value)}
                placeholder="Spoke to the contact about menu options and pricing…"
              />
            </FormField>
            <div className="flex flex-wrap items-end gap-4">
              <FormField label="Type" htmlFor="activity-type" className="w-44">
                <Select value={activityType} onValueChange={setActivityType}>
                  <SelectTrigger id="activity-type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {LOGGABLE_TYPES.map((type) => (
                      <SelectItem key={type} value={type}>
                        {humanize(type)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </FormField>
              <Button
                size="sm"
                className="mb-1"
                disabled={!summary.trim() || addActivity.isPending}
                onClick={() => void handleAdd()}
              >
                {addActivity.isPending ? "Saving…" : "Log activity"}
              </Button>
            </div>
            <p className="text-muted-foreground text-xs">
              Logging a call, email, WhatsApp message, or meeting also updates the lead&apos;s
              last-contact date.
            </p>
          </div>
        )}

        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        {isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : !entries || entries.length === 0 ? (
          <EmptyState
            icon={History}
            title="No activity yet"
            description="Log the first call or message to start this lead's history."
          />
        ) : (
          <ol className="flex flex-col gap-3">
            {entries.map((entry) => (
              <li key={entry.id} className="border-l-2 pl-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="secondary">{humanize(entry.activity_type)}</Badge>
                  <span className="text-muted-foreground text-xs">
                    {formatDateTime(entry.occurred_at)}
                  </span>
                </div>
                <p className="mt-1 text-sm whitespace-pre-wrap">{entry.summary}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </SectionCard>
  );
}
