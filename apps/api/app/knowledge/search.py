"""PostgreSQL full-text search — no embeddings, no vector search, no RAG
(CLAUDE.md section 1, section 17; this phase's own instruction section 8).

Ranking: exact `article_number` match first, then `ts_rank` over the
`search_text` tsvector (title/summary/content), then most recently updated.
Visibility is enforced after the bounded database query narrows the
candidate set to one page, not over the whole table — the same "check the
page, not the corpus" tradeoff `app.knowledge.search` documents as a
deliberate simplification for this phase's realistic data volume.
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeArticle, StaffUser
from app.knowledge.visibility import is_article_visible_to


async def search_articles(
    session: AsyncSession,
    *,
    viewer: StaffUser,
    query: str | None,
    category_id: uuid.UUID | None,
    article_type: str | None,
    department_id: uuid.UUID | None,
    status_filter: str | None,
    owner_staff_id: uuid.UUID | None,
    published_only: bool,
    page: int,
    page_size: int,
) -> tuple[list[KnowledgeArticle], int]:
    stmt = select(KnowledgeArticle)
    if published_only:
        stmt = stmt.where(KnowledgeArticle.status == "published")
    if status_filter:
        stmt = stmt.where(KnowledgeArticle.status == status_filter)
    if category_id:
        stmt = stmt.where(KnowledgeArticle.category_id == category_id)
    if article_type:
        stmt = stmt.where(KnowledgeArticle.article_type == article_type)
    if department_id:
        stmt = stmt.where(KnowledgeArticle.department_id == department_id)
    if owner_staff_id:
        stmt = stmt.where(KnowledgeArticle.owner_staff_id == owner_staff_id)

    ts_query = None
    if query:
        normalized = query.strip()
        ts_query = func.plainto_tsquery("english", normalized)
        stmt = stmt.where(
            or_(
                KnowledgeArticle.article_number.ilike(f"{normalized}%"),
                KnowledgeArticle.title.ilike(f"%{normalized}%"),
                KnowledgeArticle.search_text.op("@@")(ts_query),
            )
        )
        stmt = stmt.order_by(
            (KnowledgeArticle.article_number == normalized).desc(),
            func.ts_rank(KnowledgeArticle.search_text, ts_query).desc(),
            KnowledgeArticle.updated_at.desc(),
        )
    else:
        stmt = stmt.order_by(KnowledgeArticle.updated_at.desc())

    # Visibility filtering happens after the DB query, so pull extra rows
    # to keep the page full after exclusions — bounded (never unbounded).
    fetch_limit = page_size * 3 + 20
    candidates = (await session.scalars(stmt.limit(fetch_limit))).all()

    visible: list[KnowledgeArticle] = []
    for article in candidates:
        if await is_article_visible_to(session, article=article, viewer=viewer):
            visible.append(article)

    total = len(visible)
    start = (page - 1) * page_size
    return visible[start : start + page_size], total
