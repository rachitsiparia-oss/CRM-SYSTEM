"use client";

import { useState } from "react";
import Link from "next/link";

import {
  useAcknowledgeArticle,
  useArticleAssignments,
  useArticleDetail,
  useArticleTimeline,
  useArticleVersions,
  useCreateAssignment,
  usePublishArticle,
  useReviewArticle,
  useSubmitArticle,
  useTransitionArticle,
  useUpdateArticle,
} from "@/lib/hooks/use-knowledge";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ARTICLE_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SectionCard } from "@/components/section-card";

export function ArticleDetail({ articleId }: { articleId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: article, isLoading, isError } = useArticleDetail(articleId);
  const { data: versions } = useArticleVersions(articleId);
  const { data: timeline } = useArticleTimeline(articleId);
  const { data: assignments } = useArticleAssignments(articleId);

  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [assignStaffId, setAssignStaffId] = useState("");

  const updateArticle = useUpdateArticle(articleId);
  const submitArticle = useSubmitArticle(articleId);
  const reviewArticle = useReviewArticle(articleId);
  const publishArticle = usePublishArticle(articleId);
  const transitionArticle = useTransitionArticle(articleId);
  const acknowledgeArticle = useAcknowledgeArticle(articleId);
  const createAssignment = useCreateAssignment(articleId);

  const canUpdate = hasPermission(currentUser, "knowledge.update");
  const canReview = hasPermission(currentUser, "knowledge.review");
  const canApprove = hasPermission(currentUser, "knowledge.approve");
  const canPublish = hasPermission(currentUser, "knowledge.publish");
  const canAssign = hasPermission(currentUser, "knowledge.assign");
  const canAcknowledge = hasPermission(currentUser, "knowledge.acknowledge");

  function handleError(err: unknown) {
    setError(err instanceof ApiError ? err.message : "That action could not be completed.");
  }

  if (isLoading) return <div className="p-6 text-sm text-muted-foreground">Loading…</div>;
  if (isError || !article) {
    return <div className="p-6 text-sm text-destructive">Could not load this article.</div>;
  }

  const draftContent = content ?? article.content;
  const isEditable = article.status === "draft" || article.status === "changes_requested";

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link href="/knowledge-base/articles" className="text-sm text-muted-foreground hover:underline">
          ← Article library
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-lg font-semibold">{article.title}</h1>
          <StatusBadge
            label={humanize(article.status)}
            tone={ARTICLE_STATUS_TONES[article.status]}
          />
        </div>
        <p className="text-muted-foreground text-sm">
          {article.article_number} · {humanize(article.article_type)} · v
          {article.latest_version_number}
        </p>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="flex flex-wrap gap-2">
        {isEditable && canUpdate && content !== null && content !== article.content && (
          <Button
            size="sm"
            disabled={updateArticle.isPending}
            onClick={() =>
              updateArticle.mutate(
                { content: draftContent, version: article.version },
                { onError: handleError, onSuccess: () => setContent(null) },
              )
            }
          >
            Save content
          </Button>
        )}
        {isEditable && canReview && (
          <Button
            size="sm"
            variant="outline"
            disabled={submitArticle.isPending}
            onClick={() => submitArticle.mutate(undefined, { onError: handleError })}
          >
            Submit for review
          </Button>
        )}
        {article.status === "in_review" && canApprove && (
          <>
            <Button
              size="sm"
              disabled={reviewArticle.isPending}
              onClick={() =>
                reviewArticle.mutate(
                  { target_status: "approved" },
                  { onError: handleError },
                )
              }
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={reviewArticle.isPending}
              onClick={() =>
                reviewArticle.mutate(
                  { target_status: "changes_requested" },
                  { onError: handleError },
                )
              }
            >
              Request changes
            </Button>
          </>
        )}
        {article.status === "approved" && canPublish && (
          <Button
            size="sm"
            disabled={publishArticle.isPending}
            onClick={() => publishArticle.mutate(undefined, { onError: handleError })}
          >
            Publish
          </Button>
        )}
        {article.status === "published" && canPublish && (
          <>
            <Button
              size="sm"
              variant="outline"
              disabled={transitionArticle.isPending}
              onClick={() =>
                transitionArticle.mutate(
                  { target_status: "draft" },
                  { onError: handleError },
                )
              }
            >
              Unpublish
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={transitionArticle.isPending}
              onClick={() =>
                transitionArticle.mutate(
                  { target_status: "archived" },
                  { onError: handleError },
                )
              }
            >
              Archive
            </Button>
          </>
        )}
        {article.status === "archived" && canUpdate && (
          <Button
            size="sm"
            variant="outline"
            disabled={transitionArticle.isPending}
            onClick={() =>
              transitionArticle.mutate({ target_status: "draft" }, { onError: handleError })
            }
          >
            Reopen as draft
          </Button>
        )}
        {article.status === "published" && article.requires_acknowledgement && canAcknowledge && (
          <Button
            size="sm"
            variant="outline"
            disabled={acknowledgeArticle.isPending}
            onClick={() => acknowledgeArticle.mutate(undefined, { onError: handleError })}
          >
            Acknowledge
          </Button>
        )}
      </div>

      <Tabs defaultValue="content">
        <TabsList>
          <TabsTrigger value="content">Content</TabsTrigger>
          <TabsTrigger value="versions">Versions</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="assignments">Assignments</TabsTrigger>
        </TabsList>

        <TabsContent value="content">
          <SectionCard title="Content" description={article.summary ?? undefined}>
            {isEditable && canUpdate ? (
              <Textarea
                rows={14}
                value={draftContent}
                onChange={(e) => setContent(e.target.value)}
              />
            ) : (
              <p className="text-sm whitespace-pre-wrap">{article.content}</p>
            )}
          </SectionCard>
        </TabsContent>

        <TabsContent value="versions">
          <SectionCard title="Version history" description="Immutable snapshots taken on each submission.">
            <ul className="flex flex-col gap-3 text-sm">
              {(versions ?? []).map((version) => (
                <li key={version.id} className="border-b pb-2 last:border-none">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">v{version.version_number}</span>
                    <span className="text-muted-foreground text-xs">
                      {formatDateTime(version.submitted_at)}
                    </span>
                  </div>
                  <p className="text-muted-foreground text-xs">
                    {version.published_at
                      ? `Published ${formatDateTime(version.published_at)}`
                      : version.approved_at
                        ? `Approved ${formatDateTime(version.approved_at)}`
                        : "Awaiting review"}
                    {version.superseded_at
                      ? ` · Superseded ${formatDateTime(version.superseded_at)}`
                      : ""}
                  </p>
                </li>
              ))}
              {!versions?.length && (
                <li className="text-muted-foreground">No versions submitted yet.</li>
              )}
            </ul>
          </SectionCard>
        </TabsContent>

        <TabsContent value="timeline">
          <SectionCard title="Review timeline" description="Every submit/approve/publish/archive decision.">
            <ul className="flex flex-col gap-2 text-sm">
              {(timeline ?? []).map((event) => (
                <li key={event.id} className="flex items-center justify-between gap-2">
                  <span>{humanize(event.action)}</span>
                  <span className="text-muted-foreground text-xs">
                    {formatDateTime(event.created_at)}
                  </span>
                </li>
              ))}
              {!timeline?.length && <li className="text-muted-foreground">No history yet.</li>}
            </ul>
          </SectionCard>
        </TabsContent>

        <TabsContent value="assignments">
          <SectionCard
            title="Assignments"
            description="Staff, departments, or roles required to read this article."
            actions={
              canAssign ? (
                <div className="flex items-center gap-2">
                  <input
                    className="h-8 rounded-md border border-input bg-transparent px-2 text-sm"
                    placeholder="Staff ID"
                    value={assignStaffId}
                    onChange={(e) => setAssignStaffId(e.target.value)}
                  />
                  <Button
                    size="sm"
                    disabled={!assignStaffId.trim() || createAssignment.isPending}
                    onClick={() =>
                      createAssignment.mutate(
                        {
                          assignee_type: "staff",
                          staff_id: assignStaffId.trim(),
                          is_mandatory: true,
                        },
                        { onError: handleError, onSuccess: () => setAssignStaffId("") },
                      )
                    }
                  >
                    Assign
                  </Button>
                </div>
              ) : undefined
            }
          >
            <ul className="flex flex-col gap-2 text-sm">
              {(assignments ?? []).map((assignment) => (
                <li key={assignment.id} className="flex items-center justify-between gap-2">
                  <span>
                    {assignment.assignee_type}: {assignment.staff_id ?? assignment.department_id ?? assignment.role_id}
                  </span>
                  <StatusBadge
                    label={humanize(assignment.status)}
                    tone={assignment.status === "completed" ? "success" : "neutral"}
                  />
                </li>
              ))}
              {!assignments?.length && (
                <li className="text-muted-foreground">No assignments yet.</li>
              )}
            </ul>
          </SectionCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
