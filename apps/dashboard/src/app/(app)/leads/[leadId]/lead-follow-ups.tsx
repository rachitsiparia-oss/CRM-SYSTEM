"use client";

import { useState } from "react";
import { CalendarClock } from "lucide-react";

import {
  useCompleteFollowUp,
  useLeadFollowUps,
  useRescheduleFollowUp,
  useScheduleFollowUp,
} from "@/lib/hooks/use-leads";
import { FOLLOW_UP_STATUS_TONES, formatDateTime, humanize, isOverdue } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { StatusBadge } from "@/components/status-badge";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

const OPEN_STATUSES = ["scheduled", "due"];

export function LeadFollowUps({
  leadId,
  doNotContact,
  canEdit,
  currentStaffId,
}: {
  leadId: string;
  doNotContact: boolean;
  canEdit: boolean;
  currentStaffId: string | undefined;
}) {
  const { data: followUps, isLoading } = useLeadFollowUps(leadId);
  const scheduleFollowUp = useScheduleFollowUp(leadId);
  const completeFollowUp = useCompleteFollowUp(leadId);
  const rescheduleFollowUp = useRescheduleFollowUp(leadId);

  const [scheduledAt, setScheduledAt] = useState("");
  const [purpose, setPurpose] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [rescheduleTarget, setRescheduleTarget] = useState<string | null>(null);
  const [rescheduleAt, setRescheduleAt] = useState("");

  function reportError(fallback: string) {
    return (err: unknown) => setError(err instanceof ApiError ? err.message : fallback);
  }

  async function handleSchedule() {
    setError(null);
    if (!currentStaffId) {
      setError("Your staff profile could not be identified. Reload the page and try again.");
      return;
    }
    try {
      await scheduleFollowUp.mutateAsync({
        // `datetime-local` yields wall-clock text with no zone; the browser
        // resolves it in the user's own timezone and toISOString sends UTC,
        // which is what the API stores (CLAUDE.md section 7).
        scheduledAt: new Date(scheduledAt).toISOString(),
        assignedTo: currentStaffId,
        purpose: purpose.trim() || undefined,
      });
      setScheduledAt("");
      setPurpose("");
    } catch (err) {
      reportError("The follow-up could not be scheduled.")(err);
    }
  }

  return (
    <SectionCard
      title="Follow-ups"
      description="Scheduled contact attempts. Overdue follow-ups are flagged in the pipeline list."
    >
      <div className="flex flex-col gap-4">
        {canEdit && doNotContact && (
          <p className="border-warning/40 bg-warning/10 rounded-md border p-3 text-sm">
            This lead is marked do-not-contact, so no new follow-ups can be scheduled. Allow contact
            again from the Overview tab first.
          </p>
        )}

        {canEdit && !doNotContact && (
          <form
            className="bg-muted/40 flex flex-wrap items-end gap-4 rounded-md border p-4"
            onSubmit={(event) => {
              event.preventDefault();
              if (scheduledAt) void handleSchedule();
            }}
          >
            <FormField label="When" htmlFor="follow-up-at" required className="w-56">
              <Input
                id="follow-up-at"
                type="datetime-local"
                value={scheduledAt}
                onChange={(event) => setScheduledAt(event.target.value)}
              />
            </FormField>
            <FormField label="Purpose" htmlFor="follow-up-purpose" className="min-w-56 flex-1">
              <Input
                id="follow-up-purpose"
                value={purpose}
                onChange={(event) => setPurpose(event.target.value)}
                placeholder="What needs to be discussed?"
              />
            </FormField>
            <Button
              type="submit"
              className="mb-1"
              disabled={!scheduledAt || scheduleFollowUp.isPending}
            >
              {scheduleFollowUp.isPending ? "Scheduling…" : "Schedule follow-up"}
            </Button>
          </form>
        )}

        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        {isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : !followUps || followUps.length === 0 ? (
          <EmptyState
            icon={CalendarClock}
            title="No follow-ups scheduled"
            description="Schedule a follow-up so this enquiry doesn't go cold."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {followUps.map((followUp) => {
              const open = OPEN_STATUSES.includes(followUp.status);
              const overdue = open && isOverdue(followUp.scheduled_at);
              return (
                <li key={followUp.id} className="rounded-md border p-3">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="text-sm">
                      <p className="flex flex-wrap items-center gap-2 font-medium">
                        {formatDateTime(followUp.scheduled_at)}
                        <StatusBadge
                          label={humanize(followUp.status)}
                          tone={FOLLOW_UP_STATUS_TONES[followUp.status]}
                        />
                        {overdue && <StatusBadge label="Overdue" tone="danger" />}
                      </p>
                      {followUp.purpose && (
                        <p className="text-muted-foreground">{followUp.purpose}</p>
                      )}
                      {followUp.outcome && <p className="mt-1">Outcome: {followUp.outcome}</p>}
                    </div>

                    {canEdit && open && (
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={completeFollowUp.isPending}
                          onClick={() => {
                            setError(null);
                            completeFollowUp.mutate(
                              { followUpId: followUp.id, outcome: "Completed." },
                              { onError: reportError("The follow-up could not be completed.") },
                            );
                          }}
                        >
                          Mark complete
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setRescheduleTarget(
                              rescheduleTarget === followUp.id ? null : followUp.id,
                            );
                            setRescheduleAt("");
                          }}
                        >
                          Reschedule
                        </Button>
                      </div>
                    )}
                  </div>

                  {rescheduleTarget === followUp.id && (
                    <form
                      className="mt-3 flex flex-wrap items-end gap-3 border-t pt-3"
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (!rescheduleAt) return;
                        setError(null);
                        rescheduleFollowUp.mutate(
                          {
                            followUpId: followUp.id,
                            scheduledAt: new Date(rescheduleAt).toISOString(),
                          },
                          {
                            onSuccess: () => setRescheduleTarget(null),
                            onError: reportError("The follow-up could not be rescheduled."),
                          },
                        );
                      }}
                    >
                      <FormField label="New time" htmlFor={`reschedule-${followUp.id}`} required>
                        <Input
                          id={`reschedule-${followUp.id}`}
                          type="datetime-local"
                          value={rescheduleAt}
                          onChange={(event) => setRescheduleAt(event.target.value)}
                        />
                      </FormField>
                      <Button
                        type="submit"
                        size="sm"
                        className="mb-1"
                        disabled={!rescheduleAt || rescheduleFollowUp.isPending}
                      >
                        {rescheduleFollowUp.isPending ? "Saving…" : "Save new time"}
                      </Button>
                    </form>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}
