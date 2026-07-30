"""Skills catalogue and the per-staff skills matrix — this phase's own
instruction section 24, deliberately lightweight."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Skill, StaffSkill, StaffUser
from app.staff_operations.schemas import SkillCreateIn, StaffSkillSetIn


async def create_skill(session: AsyncSession, payload: SkillCreateIn) -> Skill:
    skill = Skill(name=payload.name, category=payload.category, description=payload.description)
    session.add(skill)
    await session.flush()
    return skill


async def list_skills(session: AsyncSession) -> list[Skill]:
    result = await session.scalars(select(Skill).where(Skill.is_active.is_(True)))
    return list(result.all())


async def set_staff_skill(
    session: AsyncSession, *, actor: StaffUser, staff_user_id: uuid.UUID, payload: StaffSkillSetIn
) -> StaffSkill:
    existing = await session.scalar(
        select(StaffSkill).where(
            StaffSkill.staff_user_id == staff_user_id, StaffSkill.skill_id == payload.skill_id
        )
    )
    if existing is not None:
        existing.proficiency_level = payload.proficiency_level
        existing.notes = payload.notes
        existing.updated_by = actor.id
        existing.version += 1
        await session.flush()
        return existing
    staff_skill = StaffSkill(
        staff_user_id=staff_user_id,
        skill_id=payload.skill_id,
        proficiency_level=payload.proficiency_level,
        notes=payload.notes,
        created_by=actor.id,
    )
    session.add(staff_skill)
    await session.flush()
    return staff_skill


async def verify_staff_skill(
    session: AsyncSession, *, actor: StaffUser, staff_skill: StaffSkill, is_verified: bool
) -> StaffSkill:
    staff_skill.is_verified = is_verified
    staff_skill.verified_by = actor.id
    staff_skill.verified_at = datetime.now(UTC)
    await session.flush()
    return staff_skill


async def list_staff_skills(session: AsyncSession, staff_user_id: uuid.UUID) -> list[StaffSkill]:
    result = await session.scalars(
        select(StaffSkill).where(StaffSkill.staff_user_id == staff_user_id)
    )
    return list(result.all())
