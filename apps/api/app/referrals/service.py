"""Referral program configuration and code issuance —
GROWTH_AND_INTELLIGENCE.md section 7.2/7.3."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.audit.service import record_audit_event
from app.db.models import ReferralCode, ReferralProgram, StaffUser
from app.referrals.errors import (
    DuplicateProgramCodeError,
    InvalidStatusTransitionError,
    MaxActiveCodesReachedError,
    ProgramNotActiveError,
)
from app.referrals.schemas import ProgramCreateIn, ProgramUpdateIn, ReferralProgramStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_PROGRAM_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"active", "archived"},
    "active": {"paused", "archived"},
    "paused": {"active", "archived"},
    "archived": set(),
}


async def list_programs(session: AsyncSession) -> list[ReferralProgram]:
    result = await session.scalars(select(ReferralProgram).order_by(ReferralProgram.created_at))
    return list(result)


async def get_program(session: AsyncSession, program_id: uuid.UUID) -> ReferralProgram | None:
    return await session.get(ReferralProgram, program_id)


async def get_default_program(session: AsyncSession) -> ReferralProgram | None:
    result: ReferralProgram | None = await session.scalar(
        select(ReferralProgram).where(
            ReferralProgram.is_active_default.is_(True), ReferralProgram.status == "active"
        )
    )
    return result


async def get_program_by_code(session: AsyncSession, code: str) -> ReferralProgram | None:
    result: ReferralProgram | None = await session.scalar(
        select(ReferralProgram).where(ReferralProgram.code == code)
    )
    return result


async def create_program(
    session: AsyncSession, *, actor: StaffUser, payload: ProgramCreateIn
) -> ReferralProgram:
    existing = await get_program_by_code(session, payload.code)
    if existing is not None:
        raise DuplicateProgramCodeError(f"Referral program code {payload.code!r} is in use.")

    program = ReferralProgram(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        status="draft",
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        referrer_eligibility_note=payload.referrer_eligibility_note,
        referee_eligibility_note=payload.referee_eligibility_note,
        qualifying_order_minimum_minor=payload.qualifying_order_minimum_minor,
        reward_ledger=payload.reward_ledger,
        referrer_reward_amount=payload.referrer_reward_amount,
        referee_reward_amount=payload.referee_reward_amount,
        max_active_codes_per_referrer=payload.max_active_codes_per_referrer,
        max_rewarded_referrals_per_window=payload.max_rewarded_referrals_per_window,
        window_days=payload.window_days,
        reward_hold_days=payload.reward_hold_days,
        version=1,
        is_active_default=False,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(program)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="referral_program.created",
        target_type="referral_program",
        target_id=program.id,
        safe_metadata={"code": program.code},
    )
    return program


async def update_program(
    session: AsyncSession, *, actor: StaffUser, program: ReferralProgram, payload: ProgramUpdateIn
) -> ReferralProgram:
    if payload.name is not None:
        program.name = payload.name
    if payload.starts_at is not None:
        program.starts_at = payload.starts_at
    if payload.ends_at is not None:
        program.ends_at = payload.ends_at
    if payload.referrer_eligibility_note is not None:
        program.referrer_eligibility_note = payload.referrer_eligibility_note
    if payload.referee_eligibility_note is not None:
        program.referee_eligibility_note = payload.referee_eligibility_note
    if payload.qualifying_order_minimum_minor is not None:
        program.qualifying_order_minimum_minor = payload.qualifying_order_minimum_minor
    if payload.referrer_reward_amount is not None:
        program.referrer_reward_amount = payload.referrer_reward_amount
    if payload.referee_reward_amount is not None:
        program.referee_reward_amount = payload.referee_reward_amount
    if payload.max_active_codes_per_referrer is not None:
        program.max_active_codes_per_referrer = payload.max_active_codes_per_referrer
    if payload.max_rewarded_referrals_per_window is not None:
        program.max_rewarded_referrals_per_window = payload.max_rewarded_referrals_per_window
    if payload.window_days is not None:
        program.window_days = payload.window_days
    if payload.reward_hold_days is not None:
        program.reward_hold_days = payload.reward_hold_days

    program.version += 1
    program.updated_by = actor.id
    await session.flush()
    return program


async def transition_program(
    session: AsyncSession,
    *,
    actor: StaffUser,
    program: ReferralProgram,
    target_status: ReferralProgramStatus,
) -> ReferralProgram:
    allowed = _PROGRAM_TRANSITIONS.get(program.status, set())
    if target_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition referral program from {program.status!r} to {target_status!r}."
        )
    program.status = target_status
    program.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="referral_program.transitioned",
        target_type="referral_program",
        target_id=program.id,
        safe_metadata={"target_status": target_status},
    )
    return program


def generate_code() -> str:
    return f"REF{uuid.uuid4().hex[:8].upper()}"


async def issue_code(
    session: AsyncSession,
    *,
    actor: StaffUser,
    program: ReferralProgram,
    referrer_customer_id: uuid.UUID,
    expires_at: datetime | None,
) -> ReferralCode:
    if program.status != "active":
        raise ProgramNotActiveError(f"Referral program {program.code!r} is not active.")

    active_count = await session.scalar(
        select(func.count())
        .select_from(ReferralCode)
        .where(
            ReferralCode.program_id == program.id,
            ReferralCode.referrer_customer_id == referrer_customer_id,
            ReferralCode.is_active.is_(True),
        )
    )
    if (active_count or 0) >= program.max_active_codes_per_referrer:
        raise MaxActiveCodesReachedError(
            f"Referrer already holds {active_count} active code(s); "
            f"the program limit is {program.max_active_codes_per_referrer}."
        )

    code = ReferralCode(
        id=uuid.uuid4(),
        code=generate_code(),
        program_id=program.id,
        referrer_customer_id=referrer_customer_id,
        is_active=True,
        expires_at=expires_at,
    )
    session.add(code)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="referral_code.issued",
        target_type="referral_code",
        target_id=code.id,
        safe_metadata={
            "program_id": str(program.id),
            "referrer_customer_id": str(referrer_customer_id),
        },
    )
    return code


async def get_code_by_value(session: AsyncSession, code_value: str) -> ReferralCode | None:
    result: ReferralCode | None = await session.scalar(
        select(ReferralCode).where(ReferralCode.code == code_value.strip().upper())
    )
    return result


async def deactivate_code(session: AsyncSession, *, code: ReferralCode) -> ReferralCode:
    code.is_active = False
    await session.flush()
    return code


def is_code_usable(code: ReferralCode, *, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if not code.is_active:
        return False
    return code.expires_at is None or now <= code.expires_at
