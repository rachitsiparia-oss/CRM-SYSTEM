"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { FeedbackStatus } from "@rkpr/contracts";

import {
  useConvertFeedbackToComplaint,
  useFeedbackDetail,
  useFeedbackRatings,
  useFeedbackStatusHistory,
  useTransitionFeedback,
} from "@/lib/hooks/use-feedback";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { FEEDBACK_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Drawer } from "@/components/modals/drawer";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const NEXT_STATUSES: Record<FeedbackStatus, FeedbackStatus[]> = {
  new: ["acknowledged", "spam"],
  acknowledged: ["under_review", "action_required", "resolved", "spam"],
  under_review: ["action_required", "resolved"],
  action_required: ["resolved"],
  resolved: ["closed"],
  closed: [],
  spam: ["closed"],
};

export function FeedbackDetailDrawer({
  feedbackId,
  onOpenChange,
}: {
  feedbackId: string | undefined;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const { data: currentUser } = useCurrentUser();
  const { data: feedback, isLoading } = useFeedbackDetail(feedbackId);
  const { data: ratings } = useFeedbackRatings(feedbackId);
  const { data: history } = useFeedbackStatusHistory(feedbackId);
  const transition = useTransitionFeedback(feedbackId ?? "");
  const convertToComplaint = useConvertFeedbackToComplaint(feedbackId ?? "");
  const [error, setError] = useState<string | null>(null);

  const canUpdate = hasPermission(currentUser, "feedback.update");
  const canConvert = hasPermission(currentUser, "feedback.convert_to_complaint");
  const nextStatuses = feedback ? NEXT_STATUSES[feedback.status] : [];

  return (
    <Drawer
      open={!!feedbackId}
      onOpenChange={onOpenChange}
      title={feedback ? feedback.feedback_number : "Feedback"}
      description={feedback ? humanize(feedback.source) : undefined}
    >
      {isLoading || !feedback ? (
        <div className="flex flex-col gap-3 py-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      ) : (
        <div className="flex flex-col gap-5 py-4">
          {error && (
            <p role="alert" className="text-destructive text-sm">
              {error}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge
              label={humanize(feedback.status)}
              tone={FEEDBACK_STATUS_TONES[feedback.status]}
            />
            {feedback.sentiment && (
              <StatusBadge
                label={humanize(feedback.sentiment)}
                tone={
                  feedback.sentiment === "positive"
                    ? "success"
                    : feedback.sentiment === "negative"
                      ? "danger"
                      : "neutral"
                }
              />
            )}
            {feedback.converted_to_complaint_id && (
              <StatusBadge label="Converted to complaint" tone="info" />
            )}
          </div>

          {feedback.comment && (
            <div>
              <p className="text-muted-foreground text-xs">Comment</p>
              <p className="text-sm">{feedback.comment}</p>
            </div>
          )}

          {ratings && ratings.length > 0 && (
            <div>
              <p className="text-muted-foreground mb-1 text-xs">Ratings</p>
              <ul className="flex flex-col gap-1 text-sm">
                {ratings.map((rating) => (
                  <li key={rating.id} className="flex items-center justify-between">
                    <span>{humanize(rating.dimension)}</span>
                    <span className="font-medium">{rating.rating} / 5</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {canUpdate && nextStatuses.length > 0 && (
            <div>
              <p className="text-muted-foreground mb-1 text-xs">Move to</p>
              <div className="flex flex-wrap gap-2">
                {nextStatuses.map((status) => (
                  <Button
                    key={status}
                    size="sm"
                    variant="outline"
                    disabled={transition.isPending}
                    onClick={() => {
                      setError(null);
                      transition.mutate(
                        { target_status: status },
                        {
                          onError: (err) =>
                            setError(
                              err instanceof ApiError ? err.message : "Could not update status.",
                            ),
                        },
                      );
                    }}
                  >
                    {humanize(status)}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {canConvert && !feedback.converted_to_complaint_id && (
            <div>
              <Button
                variant="outline"
                size="sm"
                disabled={convertToComplaint.isPending}
                onClick={() => {
                  setError(null);
                  convertToComplaint.mutate(
                    {
                      category: "other",
                      severity: "medium",
                      title: `Complaint from feedback ${feedback.feedback_number}`,
                    },
                    {
                      onSuccess: (response) =>
                        router.push(`/marketing/complaints/${response.data.complaint_id}`),
                      onError: (err) =>
                        setError(
                          err instanceof ApiError
                            ? err.message
                            : "Could not convert to a complaint.",
                        ),
                    },
                  );
                }}
              >
                Convert to complaint
              </Button>
            </div>
          )}

          {history && history.length > 0 && (
            <div>
              <p className="text-muted-foreground mb-1 text-xs">Status history</p>
              <ul className="flex flex-col gap-1.5 text-sm">
                {history.map((entry) => (
                  <li key={entry.id} className="flex items-center justify-between gap-2">
                    <span>{humanize(entry.to_status)}</span>
                    <span className="text-muted-foreground text-xs">
                      {formatDateTime(entry.created_at)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}
