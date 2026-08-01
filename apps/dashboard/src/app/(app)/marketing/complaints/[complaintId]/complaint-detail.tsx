"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import type { ComplaintStatus } from "@rkpr/contracts";

import {
  useAddComplaintNote,
  useCompleteComplaintFollowUp,
  useComplaintDetail,
  useComplaintTimeline,
  useScheduleComplaintFollowUp,
  useTransitionComplaint,
} from "@/lib/hooks/use-complaints";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import {
  COMPLAINT_PRIORITY_TONES,
  COMPLAINT_SEVERITY_TONES,
  COMPLAINT_STATUS_TONES,
  formatDateTime,
  humanize,
} from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { AssignComplaintModal } from "./assign-complaint-modal";
import { EscalateComplaintModal } from "./escalate-complaint-modal";
import { RecoveryActionsPanel } from "./recovery-actions-panel";

const NEXT_STATUSES: Record<ComplaintStatus, ComplaintStatus[]> = {
  new: ["acknowledged", "investigating", "cancelled"],
  acknowledged: ["investigating", "awaiting_customer", "awaiting_internal", "cancelled"],
  investigating: ["awaiting_customer", "awaiting_internal", "resolution_proposed", "cancelled"],
  awaiting_customer: ["investigating", "resolution_proposed", "cancelled"],
  awaiting_internal: ["investigating", "resolution_proposed", "cancelled"],
  resolution_proposed: ["investigating", "resolved", "cancelled"],
  resolved: ["closed", "reopened"],
  closed: ["reopened"],
  reopened: ["investigating", "acknowledged"],
  cancelled: [],
};

export function ComplaintDetail({ complaintId }: { complaintId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: complaint, isLoading, isError, refetch } = useComplaintDetail(complaintId);
  const { data: timeline } = useComplaintTimeline(complaintId);
  const transition = useTransitionComplaint(complaintId);
  const addNote = useAddComplaintNote(complaintId);
  const scheduleFollowUp = useScheduleComplaintFollowUp(complaintId);

  const [showAssign, setShowAssign] = useState(false);
  const [showEscalate, setShowEscalate] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [followUpAt, setFollowUpAt] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const canTransition = hasPermission(currentUser, "complaints.transition");
  const canAssign = hasPermission(currentUser, "complaints.assign");
  const canEscalate = hasPermission(currentUser, "complaints.escalate");
  const canUpdate = hasPermission(currentUser, "complaints.update");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !complaint) {
    return (
      <div className="flex-1 p-6">
        <ErrorState variant="404" title="Complaint not found" onRetry={() => void refetch()} />
      </div>
    );
  }

  const nextStatuses = NEXT_STATUSES[complaint.status];

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/marketing/complaints"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Complaints
        </Link>
      </div>

      <PageHeader
        title={complaint.complaint_number}
        description={complaint.title}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge
              label={humanize(complaint.status)}
              tone={COMPLAINT_STATUS_TONES[complaint.status]}
            />
            <StatusBadge
              label={humanize(complaint.severity)}
              tone={COMPLAINT_SEVERITY_TONES[complaint.severity]}
            />
            <StatusBadge
              label={humanize(complaint.priority)}
              tone={COMPLAINT_PRIORITY_TONES[complaint.priority]}
            />
            {complaint.is_hr_sensitive && <StatusBadge label="HR sensitive" tone="danger" />}
            {complaint.current_escalation_level > 0 && (
              <StatusBadge label={`Escalated L${complaint.current_escalation_level}`} tone="danger" />
            )}
          </div>
        }
      />

      {actionError && (
        <p role="alert" className="text-destructive text-sm">
          {actionError}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {canTransition &&
          nextStatuses.map((status) => (
            <Button
              key={status}
              size="sm"
              variant="outline"
              disabled={transition.isPending}
              onClick={() => {
                setActionError(null);
                transition.mutate(
                  { target_status: status },
                  {
                    onError: (err) =>
                      setActionError(
                        err instanceof ApiError ? err.message : "Could not update status.",
                      ),
                  },
                );
              }}
            >
              {humanize(status)}
            </Button>
          ))}
        {canAssign && (
          <Button size="sm" variant="outline" onClick={() => setShowAssign(true)}>
            Assign
          </Button>
        )}
        {canEscalate && (
          <Button size="sm" variant="outline" onClick={() => setShowEscalate(true)}>
            Escalate
          </Button>
        )}
      </div>

      <SectionCard title="Details">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground text-xs">Category</dt>
            <dd className="text-sm">{humanize(complaint.category)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Source</dt>
            <dd className="text-sm">{humanize(complaint.source_type)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Channel</dt>
            <dd className="text-sm">{complaint.channel ? humanize(complaint.channel) : "—"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">First response due</dt>
            <dd className="text-sm">{formatDateTime(complaint.first_response_due_at)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Resolution due</dt>
            <dd className="text-sm">{formatDateTime(complaint.resolution_due_at)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Follow-up due</dt>
            <dd className="text-sm">{formatDateTime(complaint.follow_up_due_at)}</dd>
          </div>
        </dl>
        <p className="mt-4 text-sm whitespace-pre-wrap">{complaint.description}</p>
        {complaint.resolution_summary && (
          <div className="mt-4">
            <p className="text-muted-foreground text-xs">Resolution summary</p>
            <p className="text-sm">{complaint.resolution_summary}</p>
          </div>
        )}
      </SectionCard>

      <RecoveryActionsPanel complaintId={complaintId} />

      <SectionCard title="Timeline" description="Aggregated activity across this complaint.">
        {!timeline || timeline.length === 0 ? (
          <p className="text-muted-foreground text-sm">No activity yet.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {timeline.map((entry, index) => (
              <li key={index} className="flex flex-col gap-1 border-b pb-3 last:border-b-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium">{entry.summary}</span>
                  <span className="text-muted-foreground text-xs">
                    {formatDateTime(entry.occurred_at)}
                  </span>
                </div>
                {entry.entry_type === "note" && typeof entry.detail.note === "string" && (
                  <p className="text-muted-foreground text-sm">{entry.detail.note}</p>
                )}
                {entry.entry_type === "follow_up" && (
                  <FollowUpTimelineDetail
                    complaintId={complaintId}
                    detail={entry.detail}
                    canUpdate={canUpdate}
                  />
                )}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      {canUpdate && (
        <SectionCard title="Add a note">
          <div className="flex flex-col gap-2">
            <Textarea
              rows={2}
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Internal note — not visible to the customer"
            />
            <div>
              <Button
                size="sm"
                disabled={!noteText.trim() || addNote.isPending}
                onClick={() => {
                  addNote.mutate(
                    { note: noteText.trim() },
                    { onSuccess: () => setNoteText("") },
                  );
                }}
              >
                {addNote.isPending ? "Saving…" : "Add note"}
              </Button>
            </div>
          </div>
        </SectionCard>
      )}

      {canUpdate && (
        <SectionCard title="Schedule a follow-up">
          <div className="flex flex-wrap items-end gap-2">
            <div className="flex flex-col gap-1.5">
              <label className="text-muted-foreground text-xs" htmlFor="follow-up-at">
                Scheduled for
              </label>
              <Input
                id="follow-up-at"
                type="datetime-local"
                value={followUpAt}
                onChange={(e) => setFollowUpAt(e.target.value)}
              />
            </div>
            <Button
              size="sm"
              disabled={!followUpAt || scheduleFollowUp.isPending}
              onClick={() => {
                scheduleFollowUp.mutate(
                  { scheduled_at: new Date(followUpAt).toISOString() },
                  { onSuccess: () => setFollowUpAt("") },
                );
              }}
            >
              {scheduleFollowUp.isPending ? "Scheduling…" : "Schedule"}
            </Button>
          </div>
        </SectionCard>
      )}

      <AssignComplaintModal
        complaintId={complaintId}
        open={showAssign}
        onOpenChange={setShowAssign}
      />
      <EscalateComplaintModal
        complaintId={complaintId}
        open={showEscalate}
        onOpenChange={setShowEscalate}
      />
    </div>
  );
}

function FollowUpTimelineDetail({
  complaintId,
  detail,
  canUpdate,
}: {
  complaintId: string;
  detail: Record<string, unknown>;
  canUpdate: boolean;
}) {
  const followUpId = typeof detail.id === "string" ? detail.id : undefined;
  const completedAt = typeof detail.completed_at === "string" ? detail.completed_at : null;
  const outcome = typeof detail.outcome === "string" ? detail.outcome : null;
  const completeFollowUp = useCompleteComplaintFollowUp(complaintId, followUpId ?? "");

  if (completedAt && outcome) {
    return (
      <p className="text-muted-foreground text-sm">Completed: {humanize(outcome)}</p>
    );
  }

  if (!canUpdate || !followUpId) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {(["satisfied", "unsatisfied", "no_response", "escalated_again"] as const).map((value) => (
        <Button
          key={value}
          size="sm"
          variant="outline"
          disabled={completeFollowUp.isPending}
          onClick={() => completeFollowUp.mutate({ outcome: value })}
        >
          {humanize(value)}
        </Button>
      ))}
    </div>
  );
}
