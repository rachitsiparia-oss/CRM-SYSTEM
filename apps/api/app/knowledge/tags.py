"""Article tags (reusing the shared `tags` table) and article relations —
this phase's own instruction section 6: "Prevent duplicate relationships
and self-links."
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    KnowledgeArticle,
    KnowledgeArticleRelation,
    KnowledgeArticleTag,
    StaffUser,
    Tag,
)
from app.knowledge.schemas import RelationCreateIn


async def assign_tags(
    session: AsyncSession, *, actor: StaffUser, article: KnowledgeArticle, tag_ids: list[uuid.UUID]
) -> None:
    for tag_id in tag_ids:
        tag = await session.get(Tag, tag_id)
        if tag is None or not tag.is_active:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Tag {tag_id} not found.")
        stmt = (
            pg_insert(KnowledgeArticleTag)
            .values(article_id=article.id, tag_id=tag_id, assigned_by=actor.id)
            .on_conflict_do_nothing(index_elements=["article_id", "tag_id"])
        )
        await session.execute(stmt)
    await session.flush()


async def remove_tag(session: AsyncSession, *, article_id: uuid.UUID, tag_id: uuid.UUID) -> None:
    link = await session.get(KnowledgeArticleTag, {"article_id": article_id, "tag_id": tag_id})
    if link is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Tag is not assigned to this article."
        )
    await session.delete(link)
    await session.flush()


async def list_article_tags(session: AsyncSession, article_id: uuid.UUID) -> list[Tag]:
    result = await session.scalars(
        select(Tag)
        .join(KnowledgeArticleTag, KnowledgeArticleTag.tag_id == Tag.id)
        .where(KnowledgeArticleTag.article_id == article_id)
    )
    return list(result.all())


async def create_relation(
    session: AsyncSession, *, actor: StaffUser, article: KnowledgeArticle, payload: RelationCreateIn
) -> KnowledgeArticleRelation:
    if payload.related_type == "knowledge_article" and payload.related_id == article.id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail="An article cannot relate to itself."
        )
    relation = KnowledgeArticleRelation(
        article_id=article.id,
        related_type=payload.related_type,
        related_id=payload.related_id,
        relation_note=payload.relation_note,
        created_by=actor.id,
    )
    session.add(relation)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This relationship already exists."
        ) from exc
    return relation


async def list_relations(
    session: AsyncSession, article_id: uuid.UUID
) -> list[KnowledgeArticleRelation]:
    result = await session.scalars(
        select(KnowledgeArticleRelation).where(KnowledgeArticleRelation.article_id == article_id)
    )
    return list(result.all())


async def remove_relation(
    session: AsyncSession, *, article_id: uuid.UUID, relation_id: uuid.UUID
) -> None:
    relation = await session.get(KnowledgeArticleRelation, relation_id)
    if relation is None or relation.article_id != article_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Relation not found.")
    await session.delete(relation)
    await session.flush()
