"""Article CRUD, immutable versioning, and the review/approval/publication
workflow — this phase's own instruction sections 2-4.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    KnowledgeAcknowledgement,
    KnowledgeArticle,
    KnowledgeArticleVersion,
    KnowledgeAssignment,
    KnowledgeReview,
    StaffUser,
)
from app.knowledge.schemas import ArticleCreateIn, ArticleUpdateIn
from app.knowledge.states import is_article_transition_allowed
from app.notifications.service import notify
from app.outbox.service import record_domain_event


def generate_article_number() -> str:
    return f"KB-{uuid.uuid4().hex[:8].upper()}"


async def get_article(session: AsyncSession, article_id: uuid.UUID) -> KnowledgeArticle | None:
    return await session.get(KnowledgeArticle, article_id)


async def get_version(
    session: AsyncSession, version_id: uuid.UUID
) -> KnowledgeArticleVersion | None:
    return await session.get(KnowledgeArticleVersion, version_id)


async def _refresh_search_text(session: AsyncSession, article: KnowledgeArticle) -> None:
    """A Core-level `UPDATE` (needed for `to_tsvector`, which the ORM can't
    express as a plain attribute assignment) bypasses the unit-of-work
    flush that `Base.__mapper_args__ = {"eager_defaults": True}` relies on,
    leaving `updated_at` expired — the exact `MissingGreenlet` trap
    `app/db/base.py` documents. `session.refresh` re-fetches the row
    within the same async context instead of lazily on next access."""
    await session.execute(
        update(KnowledgeArticle)
        .where(KnowledgeArticle.id == article.id)
        .values(
            search_text=func.to_tsvector(
                "english",
                func.concat_ws(
                    " ", article.title, func.coalesce(article.summary, ""), article.content
                ),
            )
        )
    )
    await session.refresh(article)


async def create_article(
    session: AsyncSession, *, actor: StaffUser, payload: ArticleCreateIn
) -> KnowledgeArticle:
    article = KnowledgeArticle(
        article_number=generate_article_number(),
        title=payload.title,
        summary=payload.summary,
        content=payload.content,
        article_type=payload.article_type,
        category_id=payload.category_id,
        owner_staff_id=payload.owner_staff_id or actor.id,
        department_id=payload.department_id,
        visibility_scope=payload.visibility_scope,
        status="draft",
        effective_at=payload.effective_at,
        review_at=payload.review_at,
        expiry_at=payload.expiry_at,
        estimated_reading_minutes=payload.estimated_reading_minutes,
        requires_acknowledgement=payload.requires_acknowledgement,
        requires_training=payload.requires_training,
        created_by=actor.id,
    )
    session.add(article)
    await session.flush()
    await _refresh_search_text(session, article)
    await record_domain_event(
        session,
        event_type="knowledge.article.created",
        aggregate_type="knowledge_article",
        aggregate_id=article.id,
        payload={"article_number": article.article_number},
    )
    await session.flush()
    return article


async def update_article(
    session: AsyncSession, *, actor: StaffUser, article: KnowledgeArticle, payload: ArticleUpdateIn
) -> KnowledgeArticle:
    if article.version != payload.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This article was modified by someone else. Reload and try again.",
        )
    if article.status not in ("draft", "changes_requested"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Only draft or changes-requested articles can be edited directly.",
        )
    if payload.title is not None:
        article.title = payload.title
    if payload.summary is not None:
        article.summary = payload.summary
    if payload.content is not None:
        article.content = payload.content
    if payload.category_id is not None:
        article.category_id = payload.category_id
    if payload.owner_staff_id is not None:
        article.owner_staff_id = payload.owner_staff_id
    if payload.department_id is not None:
        article.department_id = payload.department_id
    if payload.visibility_scope is not None:
        article.visibility_scope = payload.visibility_scope
    if payload.effective_at is not None:
        article.effective_at = payload.effective_at
    if payload.review_at is not None:
        article.review_at = payload.review_at
    if payload.expiry_at is not None:
        article.expiry_at = payload.expiry_at
    if payload.estimated_reading_minutes is not None:
        article.estimated_reading_minutes = payload.estimated_reading_minutes
    if payload.requires_acknowledgement is not None:
        article.requires_acknowledgement = payload.requires_acknowledgement
    if payload.requires_training is not None:
        article.requires_training = payload.requires_training
    article.updated_by = actor.id
    article.version += 1
    await session.flush()
    await _refresh_search_text(session, article)
    await session.flush()
    return article


async def submit_for_review(
    session: AsyncSession, *, actor: StaffUser, article: KnowledgeArticle
) -> KnowledgeArticle:
    if not is_article_transition_allowed(article.status, "in_review"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot submit an article from {article.status!r} for review.",
        )
    next_version_number = article.latest_version_number + 1
    version = KnowledgeArticleVersion(
        article_id=article.id,
        version_number=next_version_number,
        title_snapshot=article.title,
        summary_snapshot=article.summary,
        content_snapshot=article.content,
        author_id=actor.id,
    )
    session.add(version)
    article.status = "in_review"
    article.latest_version_number = next_version_number
    await session.flush()
    session.add(
        KnowledgeReview(
            article_id=article.id, version_id=version.id, action="submitted", actor_id=actor.id
        )
    )
    await record_domain_event(
        session,
        event_type="knowledge.article.submitted",
        aggregate_type="knowledge_article",
        aggregate_id=article.id,
        payload={"version_number": next_version_number},
    )
    await session.flush()
    return article


async def make_review_decision(
    session: AsyncSession,
    *,
    actor: StaffUser,
    article: KnowledgeArticle,
    decision: str,
    comment: str | None,
) -> KnowledgeArticle:
    if decision not in ("approved", "changes_requested"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid decision.")
    if not is_article_transition_allowed(article.status, decision):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot record a {decision!r} decision from {article.status!r}.",
        )
    version = await session.scalar(
        select(KnowledgeArticleVersion)
        .where(KnowledgeArticleVersion.article_id == article.id)
        .order_by(KnowledgeArticleVersion.version_number.desc())
        .limit(1)
    )
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="No submitted version to review.")
    # "Do not allow an unauthorized author to self-approve when policy
    # prohibits it" — this phase's own instruction section 4. Privileged
    # roles (owner/GM) are exempt, the same escape hatch other single-
    # approver workflows in this codebase allow.
    if decision == "approved" and version.author_id == actor.id and not actor.is_privileged:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You cannot approve an article you authored."
        )
    version.reviewer_id = actor.id
    if decision == "approved":
        version.approved_at = datetime.now(UTC)
    article.status = decision
    await session.flush()
    session.add(
        KnowledgeReview(
            article_id=article.id,
            version_id=version.id,
            action=decision,
            actor_id=actor.id,
            comment=comment,
        )
    )
    await record_domain_event(
        session,
        event_type=f"knowledge.article.{decision}",
        aggregate_type="knowledge_article",
        aggregate_id=article.id,
        payload={"version_id": str(version.id)},
    )
    await session.flush()
    return article


async def publish_article(
    session: AsyncSession, *, actor: StaffUser, article: KnowledgeArticle
) -> KnowledgeArticle:
    if not is_article_transition_allowed(article.status, "published"):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail=f"Cannot publish an article from {article.status!r}."
        )
    version = await session.scalar(
        select(KnowledgeArticleVersion)
        .where(KnowledgeArticleVersion.article_id == article.id)
        .order_by(KnowledgeArticleVersion.version_number.desc())
        .limit(1)
    )
    if version is None or version.approved_at is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Only an approved version can be published."
        )
    now = datetime.now(UTC)
    previous_published_id = article.published_version_id
    if previous_published_id is not None and previous_published_id != version.id:
        previous_version = await session.get(KnowledgeArticleVersion, previous_published_id)
        if previous_version is not None:
            previous_version.superseded_at = now
    version.published_at = now
    if version.effective_at is None:
        version.effective_at = now
    article.status = "published"
    article.published_version_id = version.id
    await session.flush()
    session.add(
        KnowledgeReview(
            article_id=article.id, version_id=version.id, action="published", actor_id=actor.id
        )
    )
    # A new mandatory published version invalidates any acknowledgement
    # recorded against an earlier version — this phase's own instruction
    # section 9: "Revoked acknowledgement when a new mandatory version is
    # published."
    if article.requires_acknowledgement:
        stale_acks = (
            await session.scalars(
                select(KnowledgeAcknowledgement).where(
                    KnowledgeAcknowledgement.article_id == article.id,
                    KnowledgeAcknowledgement.version_id != version.id,
                    KnowledgeAcknowledgement.revoked_at.is_(None),
                )
            )
        ).all()
        for ack in stale_acks:
            ack.revoked_at = now
        active_assignments = (
            await session.scalars(
                select(KnowledgeAssignment).where(
                    KnowledgeAssignment.article_id == article.id,
                    KnowledgeAssignment.assignee_type == "staff",
                    KnowledgeAssignment.status == "active",
                )
            )
        ).all()
        for assignment in active_assignments:
            if assignment.staff_id is not None:
                await notify(
                    session,
                    notification_type="knowledge.acknowledgement_due",
                    title=f"Updated SOP requires acknowledgement: {article.title}",
                    record_type="knowledge_article",
                    record_id=article.id,
                    recipient_staff_id=assignment.staff_id,
                    dedup_key=f"knowledge.ack_due:{article.id}:{version.id}:{assignment.staff_id}",
                )
    await record_domain_event(
        session,
        event_type="knowledge.article.published",
        aggregate_type="knowledge_article",
        aggregate_id=article.id,
        payload={"version_id": str(version.id)},
    )
    await session.flush()
    return article


async def transition_simple(
    session: AsyncSession,
    *,
    actor: StaffUser,
    article: KnowledgeArticle,
    target_status: str,
    comment: str | None,
) -> KnowledgeArticle:
    """Handles the transitions with no extra side effects beyond the
    status change and its review-log entry: unpublish, supersede, archive,
    reopen (draft)."""
    if not is_article_transition_allowed(article.status, target_status):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot move an article from {article.status!r} to {target_status!r}.",
        )
    action_map = {
        "draft": "reopened",
        "archived": "archived",
        "superseded": "superseded",
    }
    action = action_map.get(target_status, target_status)
    if article.status == "published" and target_status == "draft":
        action = "unpublished"
    previous_status = article.status
    article.status = target_status
    await session.flush()
    version_id = article.published_version_id
    if version_id is None:
        latest = await session.scalar(
            select(KnowledgeArticleVersion)
            .where(KnowledgeArticleVersion.article_id == article.id)
            .order_by(KnowledgeArticleVersion.version_number.desc())
            .limit(1)
        )
        version_id = latest.id if latest is not None else None
    if version_id is not None:
        session.add(
            KnowledgeReview(
                article_id=article.id,
                version_id=version_id,
                action=action,
                actor_id=actor.id,
                comment=comment,
            )
        )
    await record_domain_event(
        session,
        event_type=f"knowledge.article.{action}",
        aggregate_type="knowledge_article",
        aggregate_id=article.id,
        payload={"previous_status": previous_status, "new_status": target_status},
    )
    await session.flush()
    return article


async def get_article_timeline(
    session: AsyncSession, article_id: uuid.UUID
) -> list[KnowledgeReview]:
    result = await session.scalars(
        select(KnowledgeReview)
        .where(KnowledgeReview.article_id == article_id)
        .order_by(KnowledgeReview.created_at.asc())
    )
    return list(result.all())
