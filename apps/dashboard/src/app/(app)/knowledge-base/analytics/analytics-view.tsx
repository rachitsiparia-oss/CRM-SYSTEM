"use client";

import { BookOpen, FileClock, AlertTriangle, CheckCircle2, Clock3 } from "lucide-react";

import { useKnowledgeAnalytics } from "@/lib/hooks/use-knowledge";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";

export function KnowledgeAnalyticsView() {
  const { data: stats, isLoading, isError, refetch } = useKnowledgeAnalytics();

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Knowledge analytics"
        description="Publication health and acknowledgement completion across the knowledge base."
      />

      {isError ? (
        <ErrorState title="Could not load analytics" onRetry={() => void refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard
              label="Published"
              value={stats?.published_articles ?? 0}
              icon={BookOpen}
              loading={isLoading}
            />
            <StatCard
              label="Drafts awaiting review"
              value={stats?.drafts_awaiting_review ?? 0}
              icon={FileClock}
              loading={isLoading}
            />
            <StatCard
              label="Due for review"
              value={stats?.articles_due_for_review ?? 0}
              icon={Clock3}
              loading={isLoading}
            />
            <StatCard
              label="Expired"
              value={stats?.expired_articles ?? 0}
              icon={AlertTriangle}
              loading={isLoading}
            />
            <StatCard
              label="Acknowledgements completed"
              value={stats?.mandatory_acknowledgements_completed ?? 0}
              icon={CheckCircle2}
              loading={isLoading}
            />
            <StatCard
              label="Acknowledgements overdue"
              value={stats?.mandatory_acknowledgements_overdue ?? 0}
              icon={AlertTriangle}
              loading={isLoading}
            />
          </div>

          <SectionCard title="Most viewed articles">
            {stats?.most_viewed_articles.length ? (
              <ul className="flex flex-col gap-1 text-sm">
                {stats.most_viewed_articles.map((row) => (
                  <li key={row.article_id} className="flex items-center justify-between gap-2">
                    <span className="truncate">{row.title}</span>
                    <span className="text-muted-foreground shrink-0">{row.open_count} opens</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-muted-foreground text-sm">No article views recorded yet.</p>
            )}
          </SectionCard>
        </>
      )}
    </div>
  );
}
