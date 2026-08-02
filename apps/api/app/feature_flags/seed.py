"""Idempotent development seed data — a small set of default feature
flags gating capabilities this codebase already ships behind a runtime
switch. No percentage rollout or targeting fields exist to seed
(CLAUDE.md section 2's forbidden generic customization surface)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FeatureFlag, StaffUser

_FLAGS: tuple[tuple[str, str, str, bool], ...] = (
    (
        "controlled_ai.enabled",
        "Controlled AI features",
        "Master switch for AI summaries, draft replies, and anomaly narratives.",
        True,
    ),
    (
        "notifications.external_delivery",
        "External notification delivery",
        "Send in-app notifications to email/WhatsApp/SMS in addition to the bell icon.",
        True,
    ),
    (
        "scheduler.event_bus_dispatch",
        "Outbox event bus dispatch",
        "Whether the generic outbox dispatcher processes non-communication domain events.",
        True,
    ),
)


async def seed_feature_flags(session: AsyncSession) -> None:
    actor: StaffUser | None = await session.scalar(
        select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    )
    if actor is None:
        return

    for code, name, description, is_enabled in _FLAGS:
        existing = await session.scalar(select(FeatureFlag).where(FeatureFlag.code == code))
        if existing is not None:
            continue
        session.add(
            FeatureFlag(
                code=code,
                name=name,
                description=description,
                is_enabled=is_enabled,
                created_by=actor.id,
                updated_by=actor.id,
            )
        )
    await session.flush()
