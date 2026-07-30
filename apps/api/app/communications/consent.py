"""Preferences (current state), consents (append-only change log), and
suppressions, plus the pre-send evaluation pipeline this phase's own
instruction section 14 requires: before any outbound message is queued,
check channel enabled, valid destination, consent, suppression, quiet
hours, and the transactional-vs-promotional distinction.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    CommunicationChannel,
    CommunicationConsent,
    CommunicationPreference,
    CommunicationSuppression,
    StaffUser,
)


@dataclass(frozen=True)
class SendEligibility:
    allowed: bool
    reason: str | None = None


_CHANNEL_TO_FIELD_SUFFIX = {"email": "email", "sms": "sms", "whatsapp": "whatsapp"}


async def get_or_create_preference(
    session: AsyncSession, *, customer_id: uuid.UUID
) -> CommunicationPreference:
    preference = await session.scalar(
        select(CommunicationPreference).where(CommunicationPreference.customer_id == customer_id)
    )
    if preference is not None:
        return preference
    preference = CommunicationPreference(customer_id=customer_id)
    session.add(preference)
    await session.flush()
    return preference


async def record_consent(
    session: AsyncSession,
    *,
    customer_id: uuid.UUID,
    consent_type: str,
    consent_given: bool,
    source: str,
    consent_version: str | None = None,
    actor: StaffUser | None = None,
) -> CommunicationConsent:
    consent = CommunicationConsent(
        customer_id=customer_id,
        consent_type=consent_type,
        consent_given=consent_given,
        source=source,
        consent_version=consent_version,
        actor_id=actor.id if actor else None,
    )
    session.add(consent)

    preference = await get_or_create_preference(session, customer_id=customer_id)
    if consent_type == "global":
        preference.do_not_contact = not consent_given
    else:
        kind, _, channel = consent_type.partition("_")
        field_name = f"allow_{kind}_{channel}"
        if hasattr(preference, field_name):
            setattr(preference, field_name, consent_given)
    await session.flush()
    return consent


async def suppress_destination(
    session: AsyncSession,
    *,
    destination_type: str,
    destination_value: str,
    reason: str,
    scope: str = "all",
    suppressed_until: datetime | None = None,
    customer_id: uuid.UUID | None = None,
    notes: str | None = None,
) -> CommunicationSuppression:
    existing = await session.scalar(
        select(CommunicationSuppression).where(
            CommunicationSuppression.destination_type == destination_type,
            CommunicationSuppression.destination_value == destination_value,
            CommunicationSuppression.is_active.is_(True),
        )
    )
    if existing is not None:
        return existing
    suppression = CommunicationSuppression(
        destination_type=destination_type,
        destination_value=destination_value,
        reason=reason,
        scope=scope,
        suppressed_until=suppressed_until,
        customer_id=customer_id,
        notes=notes,
        is_active=True,
    )
    session.add(suppression)
    await session.flush()
    return suppression


async def lift_suppression(
    session: AsyncSession, *, suppression: CommunicationSuppression, actor: StaffUser
) -> CommunicationSuppression:
    suppression.is_active = False
    suppression.lifted_at = datetime.now(UTC)
    suppression.lifted_by = actor.id
    await session.flush()
    return suppression


async def _is_suppressed(
    session: AsyncSession, *, destination_type: str, destination_value: str, is_promotional: bool
) -> str | None:
    suppression = await session.scalar(
        select(CommunicationSuppression).where(
            CommunicationSuppression.destination_type == destination_type,
            CommunicationSuppression.destination_value == destination_value,
            CommunicationSuppression.is_active.is_(True),
        )
    )
    if suppression is None:
        return None
    now = datetime.now(UTC)
    if suppression.suppressed_until is not None and suppression.suppressed_until <= now:
        return None
    if suppression.scope == "promotional_only" and not is_promotional:
        return None
    return suppression.reason


def _within_quiet_hours(preference: CommunicationPreference, now_local_time: time) -> bool:
    start, end = preference.quiet_hours_start, preference.quiet_hours_end
    if start is None or end is None:
        return False
    if start <= end:
        return start <= now_local_time <= end
    return now_local_time >= start or now_local_time <= end  # wraps past midnight


async def evaluate_send_eligibility(
    session: AsyncSession,
    *,
    channel: CommunicationChannel,
    destination_reference: str | None,
    customer_id: uuid.UUID | None,
    is_transactional: bool,
    now_local_time: time | None = None,
) -> SendEligibility:
    if not channel.is_enabled or not channel.outbound_enabled:
        return SendEligibility(allowed=False, reason="channel_disabled")
    if not destination_reference:
        return SendEligibility(allowed=False, reason="missing_destination")

    field_suffix = _CHANNEL_TO_FIELD_SUFFIX.get(channel.code)

    if customer_id is not None:
        preference = await get_or_create_preference(session, customer_id=customer_id)
        if preference.do_not_contact:
            return SendEligibility(allowed=False, reason="do_not_contact")
        if field_suffix:
            allow_field = (
                f"allow_{'transactional' if is_transactional else 'promotional'}_{field_suffix}"
            )
            if hasattr(preference, allow_field) and not getattr(preference, allow_field):
                return SendEligibility(allowed=False, reason="no_consent")
        if (
            not is_transactional
            and now_local_time is not None
            and _within_quiet_hours(preference, now_local_time)
        ):
            return SendEligibility(allowed=False, reason="quiet_hours")

    if field_suffix in ("email", "phone") or channel.code in ("email", "sms", "whatsapp"):
        destination_type = "email" if channel.code == "email" else "phone"
        suppression_reason = await _is_suppressed(
            session,
            destination_type=destination_type,
            destination_value=destination_reference,
            is_promotional=not is_transactional,
        )
        if suppression_reason:
            return SendEligibility(allowed=False, reason=f"suppressed:{suppression_reason}")

    return SendEligibility(allowed=True)
