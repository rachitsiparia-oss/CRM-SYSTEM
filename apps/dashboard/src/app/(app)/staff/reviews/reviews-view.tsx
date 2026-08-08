"use client";

import { useState } from "react";

import type { PerformanceReview, PerformanceReviewStatus } from "@rkpr/contracts";

import { useCreatePerformanceReview, usePerformanceReviews, useTransitionPerformanceReview } from "@/lib/hooks/use-staff-operations";
import { useStaffList } from "@/lib/hooks/use-staff";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { PERFORMANCE_REVIEW_STATUS_TONES, formatDate, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const NEXT_STATUS: Partial<Record<PerformanceReviewStatus, PerformanceReviewStatus>> = {
  draft: "in_progress",
  in_progress: "submitted",
  submitted: "reviewed",
  reviewed: "finalized",
};

export function ReviewsView() {
  const { data: currentUser } = useCurrentUser();
  const canManage = hasPermission(currentUser, "staff.reviews.manage");

  const [error, setError] = useState<string | null>(null);

  const { data: staffPage } = useStaffList({ page: 1, pageSize: 100 });
  const staffOptions = staffPage?.data ?? [];

  const { data: reviews, isLoading } = usePerformanceReviews();
  const createReview = useCreatePerformanceReview();

  const [staffId, setStaffId] = useState("");
  const [cycleLabel, setCycleLabel] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");

  const staffName = (id: string) =>
    staffOptions.find((s) => s.id === id)?.display_name ?? "Unknown staff";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader title="Performance reviews" description="Structured review cycles for every staff member." />

      {error && <p className="text-sm text-destructive">{error}</p>}

      {canManage && (
        <SectionCard title="Start a review">
          <div className="flex flex-wrap items-end gap-2">
            <Select value={staffId} onValueChange={setStaffId}>
              <SelectTrigger className="w-48" aria-label="Staff member">
                <SelectValue placeholder="Staff member" />
              </SelectTrigger>
              <SelectContent>
                {staffOptions.map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.display_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              placeholder="Cycle label (e.g. 2026 H1)"
              value={cycleLabel}
              onChange={(e) => setCycleLabel(e.target.value)}
              className="w-48"
            />
            <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
            <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
            <Button
              size="sm"
              disabled={!staffId || !cycleLabel || !periodStart || !periodEnd || createReview.isPending}
              onClick={() =>
                createReview.mutate(
                  {
                    staff_user_id: staffId,
                    cycle_label: cycleLabel,
                    period_start_date: periodStart,
                    period_end_date: periodEnd,
                  },
                  {
                    onSuccess: () => {
                      setCycleLabel("");
                      setPeriodStart("");
                      setPeriodEnd("");
                    },
                    onError: (err) =>
                      setError(err instanceof ApiError ? err.message : "Could not start review."),
                  },
                )
              }
            >
              Start review
            </Button>
          </div>
        </SectionCard>
      )}

      <SectionCard title="Reviews">
        <ul className="flex flex-col gap-2 text-sm">
          {isLoading && <li className="text-muted-foreground">Loading…</li>}
          {(reviews ?? []).map((review) => (
            <ReviewRow key={review.id} review={review} staffName={staffName(review.staff_user_id)} canManage={canManage} onError={setError} />
          ))}
          {!isLoading && !reviews?.length && (
            <li className="text-muted-foreground">No reviews started yet.</li>
          )}
        </ul>
      </SectionCard>
    </div>
  );
}

function ReviewRow({
  review,
  staffName,
  canManage,
  onError,
}: {
  review: PerformanceReview;
  staffName: string;
  canManage: boolean;
  onError: (message: string) => void;
}) {
  const transition = useTransitionPerformanceReview(review.id);
  const nextStatus = NEXT_STATUS[review.status];

  return (
    <li className="flex items-center justify-between gap-2">
      <span>
        {staffName} · {review.cycle_label} · {formatDate(review.period_start_date)} –{" "}
        {formatDate(review.period_end_date)}
      </span>
      <div className="flex items-center gap-2">
        <StatusBadge label={humanize(review.status)} tone={PERFORMANCE_REVIEW_STATUS_TONES[review.status]} />
        {canManage && nextStatus && (
          <Button
            size="sm"
            variant="outline"
            disabled={transition.isPending}
            onClick={() =>
              transition.mutate(
                { target_status: nextStatus },
                {
                  onError: (err) =>
                    onError(err instanceof ApiError ? err.message : "Could not advance review."),
                },
              )
            }
          >
            Move to {humanize(nextStatus)}
          </Button>
        )}
      </div>
    </li>
  );
}
