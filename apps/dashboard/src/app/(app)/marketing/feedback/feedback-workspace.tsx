"use client";

import { useFeedbackAnalytics, useReviewRequestAnalytics } from "@/lib/hooks/use-feedback";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FeedbackList } from "./feedback-list";
import { ReviewRequestList } from "./review-request-list";

export function FeedbackWorkspace() {
  const { data: feedbackAnalytics, isLoading: feedbackLoading } = useFeedbackAnalytics();
  const { data: reviewAnalytics, isLoading: reviewLoading } = useReviewRequestAnalytics();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Feedback"
        description="Feedback entries, ratings, and post-order/post-reservation review requests."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Feedback (30d)"
          value={feedbackAnalytics?.total_30d ?? 0}
          loading={feedbackLoading}
        />
        <StatCard
          label="Average overall rating"
          value={feedbackAnalytics?.average_overall_rating?.toFixed(1) ?? "—"}
          loading={feedbackLoading}
        />
        <StatCard
          label="Converted to complaint (30d)"
          value={feedbackAnalytics?.converted_to_complaint_30d ?? 0}
          loading={feedbackLoading}
        />
        <StatCard
          label="Review request completion"
          value={
            reviewAnalytics ? `${reviewAnalytics.completion_rate_pct.toFixed(0)}%` : "—"
          }
          loading={reviewLoading}
        />
      </div>

      <Tabs defaultValue="feedback">
        <TabsList>
          <TabsTrigger value="feedback">Feedback</TabsTrigger>
          <TabsTrigger value="review-requests">Review Requests</TabsTrigger>
        </TabsList>

        <TabsContent value="feedback" className="mt-4">
          <FeedbackList />
        </TabsContent>

        <TabsContent value="review-requests" className="mt-4">
          <ReviewRequestList />
        </TabsContent>
      </Tabs>
    </div>
  );
}
