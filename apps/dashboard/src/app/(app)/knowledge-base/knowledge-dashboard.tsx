"use client";

import { useRouter } from "next/navigation";
import { BookOpen, FileClock, AlertTriangle, CheckCircle2, ListChecks, Plus } from "lucide-react";

import { useKnowledgeAnalytics } from "@/lib/hooks/use-knowledge";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { PageHeader } from "@/components/page-header";
import { StatCard } from "@/components/stat-card";
import { SectionCard } from "@/components/section-card";
import { ErrorState } from "@/components/error-state";
import { Button } from "@/components/ui/button";

export function KnowledgeDashboard() {
  const router = useRouter();
  const { data: currentUser } = useCurrentUser();
  const { data: stats, isLoading, isError, refetch } = useKnowledgeAnalytics();
  const canCreate = hasPermission(currentUser, "knowledge.create");

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <PageHeader
        title="Knowledge dashboard"
        description="SOPs, policies, checklists, and training references across the restaurant."
        actions={
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => router.push("/knowledge-base/review-queue")}>
              <ListChecks className="size-4" />
              Review queue
            </Button>
            {canCreate && (
              <Button onClick={() => router.push("/knowledge-base/articles")}>
                <Plus className="size-4" />
                New article
              </Button>
            )}
          </div>
        }
      />

      {isError ? (
        <ErrorState
          title="Could not load knowledge base stats"
          description="Dashboard statistics could not be loaded right now."
          onRetry={() => void refetch()}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Published articles"
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
              icon={AlertTriangle}
              loading={isLoading}
            />
            <StatCard
              label="Expired"
              value={stats?.expired_articles ?? 0}
              icon={AlertTriangle}
              loading={isLoading}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <SectionCard
              title="Mandatory acknowledgements"
              description="Staff who must confirm they've read a mandatory article."
            >
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-muted-foreground text-xs">Completed</p>
                  <p className="text-lg font-semibold">
                    {stats?.mandatory_acknowledgements_completed ?? 0}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Overdue</p>
                  <p className="text-lg font-semibold">
                    {stats?.mandatory_acknowledgements_overdue ?? 0}
                  </p>
                </div>
              </div>
            </SectionCard>
            <SectionCard title="Most viewed articles" description="By total open count.">
              {stats?.most_viewed_articles.length ? (
                <ul className="flex flex-col gap-1 text-sm">
                  {stats.most_viewed_articles.slice(0, 5).map((row) => (
                    <li key={row.article_id} className="flex items-center justify-between gap-2">
                      <span className="truncate">{row.title}</span>
                      <span className="text-muted-foreground shrink-0">{row.open_count}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted-foreground text-sm flex items-center gap-2">
                  <CheckCircle2 className="size-4" />
                  No article views recorded yet.
                </p>
              )}
            </SectionCard>
          </div>
        </>
      )}
    </div>
  );
}
