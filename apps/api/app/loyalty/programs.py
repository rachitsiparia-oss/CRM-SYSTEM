"""Loyalty program and tier configuration — GROWTH_AND_INTELLIGENCE.md
section 5.1/5.8. Program/tier rows are mutable configuration (not
versioned snapshots like offers) since GROWTH_AND_INTELLIGENCE.md never
asks for historical program-config replay the way it does for offers
(section 6.8's "cannot rewrite historical order calculations").
"""

import uuid
from datetime import UTC, datetime

from app.audit.service import record_audit_event
from app.db.models import LoyaltyProgram, LoyaltyTier, StaffUser
from app.loyalty.errors import DuplicateDefaultProgramError, InvalidStatusTransitionError
from app.loyalty.schemas import (
    ProgramCreateIn,
    ProgramStatus,
    ProgramUpdateIn,
    TierCreateIn,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_PROGRAM_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active", "archived"},
    "active": {"paused", "archived"},
    "paused": {"active", "archived"},
    "archived": set(),
}


async def list_programs(session: AsyncSession) -> list[LoyaltyProgram]:
    result = await session.scalars(select(LoyaltyProgram).order_by(LoyaltyProgram.created_at))
    return list(result)


async def get_program(session: AsyncSession, program_id: uuid.UUID) -> LoyaltyProgram | None:
    return await session.get(LoyaltyProgram, program_id)


async def get_default_program(session: AsyncSession) -> LoyaltyProgram | None:
    result: LoyaltyProgram | None = await session.scalar(
        select(LoyaltyProgram).where(
            LoyaltyProgram.is_default.is_(True), LoyaltyProgram.status == "active"
        )
    )
    return result


async def get_program_by_code(session: AsyncSession, code: str) -> LoyaltyProgram | None:
    result: LoyaltyProgram | None = await session.scalar(
        select(LoyaltyProgram).where(LoyaltyProgram.code == code)
    )
    return result


async def create_program(
    session: AsyncSession, *, actor: StaffUser, payload: ProgramCreateIn
) -> LoyaltyProgram:
    if payload.is_default:
        existing_default = await session.scalar(
            select(LoyaltyProgram).where(
                LoyaltyProgram.is_default.is_(True), LoyaltyProgram.status == "active"
            )
        )
        if existing_default is not None:
            raise DuplicateDefaultProgramError(
                "Only one default active loyalty program may exist at a time; "
                f"{existing_default.code!r} is already the default."
            )

    program = LoyaltyProgram(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        points_display_name=payload.points_display_name,
        description=payload.description,
        points_per_currency_unit=payload.points_per_currency_unit,
        currency_unit_minor=payload.currency_unit_minor,
        redemption_points_per_unit=payload.redemption_points_per_unit,
        redemption_value_minor=payload.redemption_value_minor,
        minimum_redemption_points=payload.minimum_redemption_points,
        max_redemption_percent=payload.max_redemption_percent,
        points_expiry_days=payload.points_expiry_days,
        terms_summary=payload.terms_summary,
        is_default=payload.is_default,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(program)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="loyalty.program.created",
        target_type="loyalty_program",
        target_id=program.id,
        safe_metadata={"code": program.code},
    )
    return program


async def update_program(
    session: AsyncSession, *, actor: StaffUser, program: LoyaltyProgram, payload: ProgramUpdateIn
) -> LoyaltyProgram:
    if payload.name is not None:
        program.name = payload.name
    if payload.description is not None:
        program.description = payload.description
    if payload.points_expiry_days is not None:
        program.points_expiry_days = payload.points_expiry_days
    if payload.max_redemption_percent is not None:
        program.max_redemption_percent = payload.max_redemption_percent
    if payload.terms_summary is not None:
        program.terms_summary = payload.terms_summary
    program.updated_by = actor.id
    await session.flush()
    return program


async def transition_program(
    session: AsyncSession,
    *,
    actor: StaffUser,
    program: LoyaltyProgram,
    target_status: ProgramStatus,
) -> LoyaltyProgram:
    allowed = _PROGRAM_TRANSITIONS.get(program.status, set())
    if target_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition loyalty program from {program.status!r} to {target_status!r}."
        )
    if target_status == "active" and program.is_default:
        existing_default = await session.scalar(
            select(LoyaltyProgram).where(
                LoyaltyProgram.is_default.is_(True),
                LoyaltyProgram.status == "active",
                LoyaltyProgram.id != program.id,
            )
        )
        if existing_default is not None:
            raise DuplicateDefaultProgramError(
                f"{existing_default.code!r} is already the default active program."
            )

    now = datetime.now(UTC)
    program.status = target_status
    if target_status == "active" and program.activated_at is None:
        program.activated_at = now
    if target_status == "archived":
        program.archived_at = now
    program.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="loyalty.program.transitioned",
        target_type="loyalty_program",
        target_id=program.id,
        safe_metadata={"target_status": target_status},
    )
    return program


async def list_tiers(session: AsyncSession, program_id: uuid.UUID) -> list[LoyaltyTier]:
    result = await session.scalars(
        select(LoyaltyTier).where(LoyaltyTier.program_id == program_id).order_by(LoyaltyTier.rank)
    )
    return list(result)


async def create_tier(
    session: AsyncSession, *, actor: StaffUser, program: LoyaltyProgram, payload: TierCreateIn
) -> LoyaltyTier:
    tier = LoyaltyTier(
        id=uuid.uuid4(),
        program_id=program.id,
        code=payload.code,
        name=payload.name,
        rank=payload.rank,
        qualification_metric=payload.qualification_metric,
        threshold=payload.threshold,
        rolling_window_days=payload.rolling_window_days,
        benefits_summary=payload.benefits_summary,
        points_multiplier=payload.points_multiplier,
        review_period_days=payload.review_period_days,
        downgrade_grace_days=payload.downgrade_grace_days,
        icon=payload.icon,
        color=payload.color,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(tier)
    await session.flush()
    return tier
