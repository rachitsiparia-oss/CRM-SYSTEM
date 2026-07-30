"""Knowledge base analytics — this phase's own instruction section 11.
All counts are database-side aggregates (CLAUDE.md section 5.2), not raw
rows loaded into application memory. "Avoid misleading view counts caused
by repeated automated requests" is satisfied by `KnowledgeAcknowledgement.
open_count` only ever being incremented by an authenticated staff member
opening the article detail page — there is no automated/bot traffic path
in this codebase that would inflate it.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeAcknowledgement, KnowledgeArticle


async def get_knowledge_analytics(session: AsyncSession) -> dict[str, object]:
    now = datetime.now(UTC)

    published_articles = await session.scalar(
        select(func.count())
        .select_from(KnowledgeArticle)
        .where(KnowledgeArticle.status == "published")
    )
    drafts_awaiting_review = await session.scalar(
        select(func.count())
        .select_from(KnowledgeArticle)
        .where(KnowledgeArticle.status.in_(("draft", "in_review", "changes_requested")))
    )
    articles_due_for_review = await session.scalar(
        select(func.count())
        .select_from(KnowledgeArticle)
        .where(KnowledgeArticle.status == "published", KnowledgeArticle.review_at <= now)
    )
    expired_articles = await session.scalar(
        select(func.count())
        .select_from(KnowledgeArticle)
        .where(KnowledgeArticle.status == "published", KnowledgeArticle.expiry_at <= now)
    )
    mandatory_completed = await session.scalar(
        select(func.count())
        .select_from(KnowledgeAcknowledgement)
        .where(
            KnowledgeAcknowledgement.acknowledged_at.is_not(None),
            KnowledgeAcknowledgement.revoked_at.is_(None),
        )
    )
    mandatory_overdue = await session.scalar(
        select(func.count())
        .select_from(KnowledgeAcknowledgement)
        .where(
            KnowledgeAcknowledgement.acknowledged_at.is_(None),
            KnowledgeAcknowledgement.revoked_at.is_(None),
            KnowledgeAcknowledgement.due_at.is_not(None),
            KnowledgeAcknowledgement.due_at <= now,
        )
    )
    most_viewed_rows = (
        await session.execute(
            select(
                KnowledgeArticle.id,
                KnowledgeArticle.title,
                func.sum(KnowledgeAcknowledgement.open_count),
            )
            .join(
                KnowledgeAcknowledgement, KnowledgeAcknowledgement.article_id == KnowledgeArticle.id
            )
            .group_by(KnowledgeArticle.id, KnowledgeArticle.title)
            .order_by(func.sum(KnowledgeAcknowledgement.open_count).desc())
            .limit(10)
        )
    ).all()

    return {
        "published_articles": published_articles or 0,
        "drafts_awaiting_review": drafts_awaiting_review or 0,
        "articles_due_for_review": articles_due_for_review or 0,
        "expired_articles": expired_articles or 0,
        "mandatory_acknowledgements_completed": mandatory_completed or 0,
        "mandatory_acknowledgements_overdue": mandatory_overdue or 0,
        "most_viewed_articles": [
            {"article_id": str(row[0]), "title": row[1], "open_count": int(row[2] or 0)}
            for row in most_viewed_rows
        ],
    }
