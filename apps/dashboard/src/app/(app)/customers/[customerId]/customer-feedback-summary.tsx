"use client";

import Link from "next/link";

import { useCustomerFeedbackHistory } from "@/lib/hooks/use-feedback";
import { useComplaintList } from "@/lib/hooks/use-complaints";
import { useRecoveryActionList } from "@/lib/hooks/use-service-recovery";
import {
  COMPLAINT_SEVERITY_TONES,
  COMPLAINT_STATUS_TONES,
  FEEDBACK_STATUS_TONES,
  RECOVERY_STATUS_TONES,
  formatDateTime,
  formatMinorUnits,
  humanize,
} from "@/lib/crm-display";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";

const PAGE_SIZE = 5;

export function CustomerFeedbackSummary({ customerId }: { customerId: string }) {
  const { data: feedback, isLoading: feedbackLoading } = useCustomerFeedbackHistory(customerId, {
    page: 1,
    pageSize: PAGE_SIZE,
  });
  const { data: complaints, isLoading: complaintsLoading } = useComplaintList({
    page: 1,
    pageSize: PAGE_SIZE,
    customerId,
  });
  const { data: recoveryActions, isLoading: recoveryLoading } = useRecoveryActionList({
    page: 1,
    pageSize: PAGE_SIZE,
    customerId,
  });

  return (
    <div className="flex flex-col gap-4">
      <SectionCard
        title="Feedback"
        description="Ratings and comments left by this customer."
        actions={
          <Link href="/marketing/feedback" className="text-muted-foreground text-sm hover:underline">
            Open feedback
          </Link>
        }
      >
        {feedbackLoading ? (
          <p className="text-muted-foreground text-sm">Loading…</p>
        ) : feedback && feedback.data.length > 0 ? (
          <ul className="flex flex-col gap-2 text-sm">
            {feedback.data.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 flex-col">
                  <span className="truncate font-medium">{entry.feedback_number}</span>
                  {entry.comment && (
                    <span className="text-muted-foreground truncate text-xs">{entry.comment}</span>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {entry.sentiment && (
                    <StatusBadge
                      label={humanize(entry.sentiment)}
                      tone={
                        entry.sentiment === "positive"
                          ? "success"
                          : entry.sentiment === "negative"
                            ? "danger"
                            : "neutral"
                      }
                    />
                  )}
                  <StatusBadge
                    label={humanize(entry.status)}
                    tone={FEEDBACK_STATUS_TONES[entry.status]}
                  />
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground text-sm">No feedback on file.</p>
        )}
      </SectionCard>

      <SectionCard
        title="Complaints"
        description="Complaint severity and resolution state."
        actions={
          <Link
            href="/marketing/complaints"
            className="text-muted-foreground text-sm hover:underline"
          >
            Open complaints
          </Link>
        }
      >
        {complaintsLoading ? (
          <p className="text-muted-foreground text-sm">Loading…</p>
        ) : complaints && complaints.data.length > 0 ? (
          <ul className="flex flex-col gap-2 text-sm">
            {complaints.data.map((complaint) => (
              <li key={complaint.id} className="flex items-center justify-between gap-2">
                <Link
                  href={`/marketing/complaints/${complaint.id}`}
                  className="min-w-0 truncate hover:underline"
                >
                  {complaint.complaint_number} — {complaint.title}
                </Link>
                <div className="flex shrink-0 items-center gap-2">
                  <StatusBadge
                    label={humanize(complaint.severity)}
                    tone={COMPLAINT_SEVERITY_TONES[complaint.severity]}
                  />
                  <StatusBadge
                    label={humanize(complaint.status)}
                    tone={COMPLAINT_STATUS_TONES[complaint.status]}
                  />
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground text-sm">No complaints on file.</p>
        )}
      </SectionCard>

      <SectionCard
        title="Service recovery"
        description="Compensation proposed or executed for this customer."
        actions={
          <Link
            href="/marketing/service-recovery"
            className="text-muted-foreground text-sm hover:underline"
          >
            Open service recovery
          </Link>
        }
      >
        {recoveryLoading ? (
          <p className="text-muted-foreground text-sm">Loading…</p>
        ) : recoveryActions && recoveryActions.data.length > 0 ? (
          <ul className="flex flex-col gap-2 text-sm">
            {recoveryActions.data.map((action) => (
              <li key={action.id} className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 flex-col">
                  <span className="truncate font-medium">{humanize(action.recovery_type)}</span>
                  <span className="text-muted-foreground text-xs">
                    {formatDateTime(action.proposed_at)}
                  </span>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-muted-foreground text-xs">
                    {action.value_minor !== null
                      ? formatMinorUnits(action.value_minor)
                      : action.points !== null
                        ? `${action.points} pts`
                        : ""}
                  </span>
                  <StatusBadge
                    label={humanize(action.status)}
                    tone={RECOVERY_STATUS_TONES[action.status]}
                  />
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted-foreground text-sm">No service recovery activity on file.</p>
        )}
      </SectionCard>
    </div>
  );
}
