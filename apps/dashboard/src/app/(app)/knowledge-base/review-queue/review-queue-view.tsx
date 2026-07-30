"use client";

import Link from "next/link";

import { useArticleList } from "@/lib/hooks/use-knowledge";
import { ARTICLE_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { ErrorState } from "@/components/error-state";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";

export function ReviewQueueView() {
  const { data, isLoading, isError, refetch } = useArticleList({
    page: 1,
    pageSize: 50,
    status: "in_review",
  });

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Review queue"
        description="Articles submitted for review, awaiting an approve or request-changes decision."
      />

      {isError ? (
        <ErrorState title="Could not load the review queue" onRetry={() => void refetch()} />
      ) : isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      ) : !data?.data.length ? (
        <EmptyState title="Nothing awaiting review" description="The review queue is empty." />
      ) : (
        <ul className="flex flex-col gap-2">
          {data.data.map((article) => (
            <li key={article.id} className="rounded-lg border p-4">
              <Link
                href={`/knowledge-base/articles/${article.id}`}
                className="flex items-center justify-between gap-3"
              >
                <div>
                  <p className="font-medium hover:underline">{article.title}</p>
                  <p className="text-muted-foreground text-xs">
                    {article.article_number} · {humanize(article.article_type)} · submitted v
                    {article.latest_version_number}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-muted-foreground text-xs">
                    {formatDateTime(article.updated_at)}
                  </span>
                  <StatusBadge
                    label={humanize(article.status)}
                    tone={ARTICLE_STATUS_TONES[article.status]}
                  />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
