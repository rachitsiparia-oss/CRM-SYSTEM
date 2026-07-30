"""Category CRUD with ancestry-cycle prevention — this phase's own
instruction section 1: "Prevent cycles in category ancestry." A CHECK
constraint can only stop a category from being its own direct parent
(`knowledge_category.py`'s `valid_parent_not_self`); a multi-level cycle
(A -> B -> A) needs a live ancestor walk, done here.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KnowledgeCategory, StaffUser
from app.knowledge.schemas import CategoryCreateIn, CategoryUpdateIn


async def _would_create_cycle(
    session: AsyncSession, *, category_id: uuid.UUID, proposed_parent_id: uuid.UUID
) -> bool:
    current_id: uuid.UUID | None = proposed_parent_id
    seen: set[uuid.UUID] = set()
    while current_id is not None:
        if current_id == category_id:
            return True
        if current_id in seen:
            return True
        seen.add(current_id)
        parent = await session.get(KnowledgeCategory, current_id)
        if parent is None:
            return False
        current_id = parent.parent_id
    return False


async def get_category(session: AsyncSession, category_id: uuid.UUID) -> KnowledgeCategory | None:
    return await session.get(KnowledgeCategory, category_id)


async def create_category(
    session: AsyncSession, *, actor: StaffUser, payload: CategoryCreateIn
) -> KnowledgeCategory:
    category = KnowledgeCategory(
        parent_id=payload.parent_id,
        name=payload.name,
        code=payload.code,
        description=payload.description,
        sort_order=payload.sort_order,
        created_by=actor.id,
    )
    session.add(category)
    await session.flush()
    if payload.parent_id is not None and await _would_create_cycle(
        session, category_id=category.id, proposed_parent_id=payload.parent_id
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This would create a category ancestry cycle."
        )
    return category


async def update_category(
    session: AsyncSession,
    *,
    actor: StaffUser,
    category: KnowledgeCategory,
    payload: CategoryUpdateIn,
) -> KnowledgeCategory:
    if category.version != payload.version:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="This category was modified by someone else. Reload and try again.",
        )
    if payload.parent_id is not None and await _would_create_cycle(
        session, category_id=category.id, proposed_parent_id=payload.parent_id
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="This would create a category ancestry cycle."
        )
    if payload.name is not None:
        category.name = payload.name
    if payload.description is not None:
        category.description = payload.description
    if payload.parent_id is not None:
        category.parent_id = payload.parent_id
    if payload.sort_order is not None:
        category.sort_order = payload.sort_order
    if payload.is_active is not None:
        category.is_active = payload.is_active
    category.updated_by = actor.id
    category.version += 1
    await session.flush()
    return category


async def list_categories(session: AsyncSession) -> list[KnowledgeCategory]:
    result = await session.scalars(
        select(KnowledgeCategory).order_by(KnowledgeCategory.sort_order, KnowledgeCategory.name)
    )
    return list(result.all())
