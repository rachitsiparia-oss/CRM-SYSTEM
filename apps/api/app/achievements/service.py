"""Achievement definition CRUD — GROWTH_AND_INTELLIGENCE.md section 8.2."""

from __future__ import annotations

import uuid

from app.achievements.errors import DuplicateAchievementCodeError
from app.achievements.schemas import AchievementCreateIn, AchievementUpdateIn
from app.audit.service import record_audit_event
from app.db.models import Achievement, StaffUser
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_achievements(
    session: AsyncSession, *, page: int, page_size: int, is_active: bool | None = None
) -> tuple[list[Achievement], int]:
    query = select(Achievement)
    count_query = select(func.count()).select_from(Achievement)
    if is_active is not None:
        query = query.where(Achievement.is_active == is_active)
        count_query = count_query.where(Achievement.is_active == is_active)

    total = await session.scalar(count_query)
    rows = await session.scalars(
        query.order_by(Achievement.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows), total or 0


async def get_achievement(session: AsyncSession, achievement_id: uuid.UUID) -> Achievement | None:
    return await session.get(Achievement, achievement_id)


async def get_achievement_by_code(session: AsyncSession, code: str) -> Achievement | None:
    result: Achievement | None = await session.scalar(
        select(Achievement).where(Achievement.code == code)
    )
    return result


async def create_achievement(
    session: AsyncSession, *, actor: StaffUser, payload: AchievementCreateIn
) -> Achievement:
    existing = await get_achievement_by_code(session, payload.code)
    if existing is not None:
        raise DuplicateAchievementCodeError(f"Achievement code {payload.code!r} is already in use.")

    achievement = Achievement(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
        condition_version=1,
        condition=payload.condition.model_dump(mode="json"),
        is_active=payload.is_active,
        is_hidden=payload.is_hidden,
        reward_ledger=payload.reward_ledger,
        reward_amount=payload.reward_amount,
        is_repeatable=payload.is_repeatable,
        cooldown_days=payload.cooldown_days,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(achievement)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="achievement.created",
        target_type="achievement",
        target_id=achievement.id,
        safe_metadata={"code": achievement.code},
    )
    return achievement


async def update_achievement(
    session: AsyncSession,
    *,
    actor: StaffUser,
    achievement: Achievement,
    payload: AchievementUpdateIn,
) -> Achievement:
    if payload.name is not None:
        achievement.name = payload.name
    if payload.description is not None:
        achievement.description = payload.description
    if payload.icon is not None:
        achievement.icon = payload.icon
    if payload.condition is not None:
        achievement.condition = payload.condition.model_dump(mode="json")
        achievement.condition_version += 1
    if payload.is_active is not None:
        achievement.is_active = payload.is_active
    if payload.is_hidden is not None:
        achievement.is_hidden = payload.is_hidden
    if payload.reward_ledger is not None:
        achievement.reward_ledger = payload.reward_ledger
    if payload.reward_amount is not None:
        achievement.reward_amount = payload.reward_amount
    if payload.is_repeatable is not None:
        achievement.is_repeatable = payload.is_repeatable
    if payload.cooldown_days is not None:
        achievement.cooldown_days = payload.cooldown_days

    achievement.updated_by = actor.id
    await session.flush()
    return achievement
