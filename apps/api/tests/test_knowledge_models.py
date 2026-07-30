import uuid

import pytest
from app.db.models import (
    KnowledgeArticle,
    KnowledgeArticleRelation,
    KnowledgeAssignment,
    KnowledgeCategory,
    KnowledgeVisibilityRule,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _category_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {"id": uuid.uuid4(), "name": "Test Category", "code": f"cat-{suffix}"}
    base.update(overrides)
    return base


def _article_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "article_number": f"KB-{suffix}",
        "title": "Test Article",
        "content": "Some content.",
        "article_type": "sop",
        "visibility_scope": "all_staff",
        "status": "draft",
    }
    base.update(overrides)
    return base


async def _make_article(session: AsyncSession, **overrides: object) -> KnowledgeArticle:
    article = KnowledgeArticle(**_article_kwargs(**overrides))
    session.add(article)
    await session.flush()
    return article


async def test_category_cannot_be_its_own_parent(db_session: AsyncSession) -> None:
    category_id = uuid.uuid4()
    category = KnowledgeCategory(**_category_kwargs(id=category_id, parent_id=category_id))
    db_session.add(category)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_article_rejects_invalid_type(db_session: AsyncSession) -> None:
    article = KnowledgeArticle(**_article_kwargs(article_type="not_a_real_type"))
    db_session.add(article)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_article_rejects_invalid_status(db_session: AsyncSession) -> None:
    article = KnowledgeArticle(**_article_kwargs(status="not_a_real_status"))
    db_session.add(article)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_article_rejects_invalid_visibility_scope(db_session: AsyncSession) -> None:
    article = KnowledgeArticle(**_article_kwargs(visibility_scope="everyone_ever"))
    db_session.add(article)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_article_relation_rejects_self_link(db_session: AsyncSession) -> None:
    article = await _make_article(db_session)
    relation = KnowledgeArticleRelation(
        id=uuid.uuid4(),
        article_id=article.id,
        related_type="knowledge_article",
        related_id=article.id,
    )
    db_session.add(relation)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_article_relation_rejects_duplicate(db_session: AsyncSession) -> None:
    article = await _make_article(db_session)
    other_id = uuid.uuid4()
    db_session.add(
        KnowledgeArticleRelation(
            id=uuid.uuid4(), article_id=article.id, related_type="menu_item", related_id=other_id
        )
    )
    await db_session.flush()
    db_session.add(
        KnowledgeArticleRelation(
            id=uuid.uuid4(), article_id=article.id, related_type="menu_item", related_id=other_id
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_visibility_rule_requires_exactly_one_target(db_session: AsyncSession) -> None:
    article = await _make_article(db_session)
    rule = KnowledgeVisibilityRule(
        id=uuid.uuid4(),
        article_id=article.id,
        rule_type="department",
        department_id=None,
    )
    db_session.add(rule)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_assignment_requires_matching_target(db_session: AsyncSession) -> None:
    article = await _make_article(db_session)
    assignment = KnowledgeAssignment(
        id=uuid.uuid4(),
        article_id=article.id,
        assignee_type="staff",
        staff_id=None,
    )
    db_session.add(assignment)
    with pytest.raises(IntegrityError):
        await db_session.flush()
