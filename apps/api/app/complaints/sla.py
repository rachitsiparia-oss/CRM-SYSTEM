"""SLA policy selection and business-hours-aware due-date calculation —
instruction section 5.3/13. No "add N business hours, skipping closed
periods" calculator exists anywhere else in the codebase; this one reads
Phase 9's `business_hours`/`holiday_calendar` tables as the single source
of truth for operating hours rather than re-deriving them
(`app.reservations.availability.get_business_hours_for_date`).

Every function here is a deterministic, idempotent, directly-callable unit
— the "engine, not scheduler" split every prior phase's own reminder/
scheduled-outreach system used. Live recurring invocation through
`apps/worker` is Phase 15's scope, not this one's.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.complaints.schemas import SlaPolicyCreateIn, SlaPolicyUpdateIn
from app.db.models import Complaint, ComplaintSlaEvent, SlaPolicy
from app.reservations.availability import get_business_hours_for_date

RESTAURANT_TIMEZONE = ZoneInfo("Asia/Kolkata")

# How close to a due timestamp counts as "approaching" — instruction
# section 5.3/13's "identify approaching SLA breaches".
APPROACHING_THRESHOLD = timedelta(minutes=30)

SLA_EVENT_TYPES_BY_MILESTONE: dict[str, tuple[str, str]] = {
    "first_response_due_at": ("approaching_first_response", "breached_first_response"),
    "acknowledgement_due_at": ("approaching_acknowledgement", "breached_acknowledgement"),
    "resolution_due_at": ("approaching_resolution", "breached_resolution"),
    "follow_up_due_at": ("approaching_follow_up", "breached_follow_up"),
}


async def compute_due_at(
    session: AsyncSession, *, base_time: datetime, minutes: int, business_hours_only: bool
) -> datetime:
    """Adds `minutes` to `base_time`, skipping periods outside configured
    operating hours when `business_hours_only`. Walks forward day by day
    (bounded to 60 days as a safety net against a misconfigured or empty
    weekly schedule — real restaurant hours never require more than a
    handful)."""
    if not business_hours_only:
        return base_time + timedelta(minutes=minutes)

    remaining = timedelta(minutes=minutes)
    cursor = base_time.astimezone(RESTAURANT_TIMEZONE)

    for _ in range(60):
        current_date: date = cursor.date()
        business_hours, holiday = await get_business_hours_for_date(session, current_date)

        if holiday is not None:
            is_closed = holiday.is_closed
            opens_at, closes_at, closes_next_day = holiday.opens_at, holiday.closes_at, False
        elif business_hours is not None:
            is_closed = business_hours.is_closed
            opens_at = business_hours.opens_at
            closes_at = business_hours.closes_at
            closes_next_day = business_hours.closes_next_day
        else:
            is_closed, opens_at, closes_at, closes_next_day = True, None, None, False

        if not is_closed and opens_at is not None and closes_at is not None:
            day_open = datetime.combine(current_date, opens_at, tzinfo=RESTAURANT_TIMEZONE)
            close_date = current_date + timedelta(days=1) if closes_next_day else current_date
            day_close = datetime.combine(close_date, closes_at, tzinfo=RESTAURANT_TIMEZONE)

            window_start = max(cursor, day_open)
            if window_start < day_close:
                available = day_close - window_start
                if available >= remaining:
                    return (window_start + remaining).astimezone(UTC)
                remaining -= available

        next_day = current_date + timedelta(days=1)
        cursor = datetime.combine(next_day, time(0, 0), tzinfo=RESTAURANT_TIMEZONE)

    return (cursor + remaining).astimezone(UTC)


def _policy_specificity(policy: SlaPolicy) -> int:
    score = 0
    if policy.applicable_categories is not None:
        score += 2
    if policy.applicable_severities is not None:
        score += 1
    return score


async def select_sla_policy(
    session: AsyncSession, *, category: str, severity: str
) -> SlaPolicy | None:
    """The most specific active policy matching both `category` and
    `severity` wins; a `NULL` list matches any value. Ties broken by
    `created_at` (the earliest-defined matching policy wins) for
    determinism."""
    rows = list(
        (await session.scalars(select(SlaPolicy).where(SlaPolicy.is_active.is_(True)))).all()
    )
    matching = [
        policy
        for policy in rows
        if (policy.applicable_categories is None or category in policy.applicable_categories)
        and (policy.applicable_severities is None or severity in policy.applicable_severities)
    ]
    if not matching:
        return None
    matching.sort(key=lambda p: (-_policy_specificity(p), p.created_at))
    return matching[0]


async def apply_sla_to_complaint(session: AsyncSession, *, complaint: Complaint) -> None:
    """Selects a matching policy (if any) and sets every due-at field from
    `complaint.created_at`. A complaint with no matching policy simply has
    no SLA due dates — not an error, since SLA policy coverage is
    optional/configurable."""
    policy = await select_sla_policy(
        session, category=complaint.category, severity=complaint.severity
    )
    if policy is None:
        return

    complaint.sla_policy_id = policy.id
    base = complaint.created_at
    complaint.first_response_due_at = await compute_due_at(
        session,
        base_time=base,
        minutes=policy.first_response_minutes,
        business_hours_only=policy.business_hours_only,
    )
    complaint.acknowledgement_due_at = await compute_due_at(
        session,
        base_time=base,
        minutes=policy.acknowledgement_minutes,
        business_hours_only=policy.business_hours_only,
    )
    complaint.resolution_due_at = await compute_due_at(
        session,
        base_time=base,
        minutes=policy.resolution_minutes,
        business_hours_only=policy.business_hours_only,
    )
    if policy.follow_up_minutes is not None:
        complaint.follow_up_due_at = await compute_due_at(
            session,
            base_time=base,
            minutes=policy.follow_up_minutes,
            business_hours_only=policy.business_hours_only,
        )


def _dedup_key(complaint_id: uuid.UUID, event_type: str) -> str:
    return f"complaint:{complaint_id}:{event_type}"


async def detect_sla_events(
    session: AsyncSession, *, now: datetime | None = None
) -> list[ComplaintSlaEvent]:
    """Deterministic and idempotent: re-running this against the same
    complaint state never creates a duplicate row for an event type already
    recorded (`dedup_key` is unique). Returns newly-created events only —
    callers (e.g. a future Phase 15 scheduled job, or
    `app.complaints.service.run_sla_escalations` today) decide what to do
    with a breach, this function only detects and records it."""
    now = now or datetime.now(UTC)
    open_complaints = list(
        (
            await session.scalars(
                select(Complaint).where(
                    Complaint.status.not_in(["resolved", "closed", "cancelled"]),
                    Complaint.sla_policy_id.is_not(None),
                )
            )
        ).all()
    )

    created: list[ComplaintSlaEvent] = []
    for complaint in open_complaints:
        milestones: list[tuple[str, datetime | None, datetime | None]] = [
            (
                "first_response_due_at",
                complaint.first_response_due_at,
                complaint.first_responded_at,
            ),
            ("acknowledgement_due_at", complaint.acknowledgement_due_at, complaint.acknowledged_at),
            ("resolution_due_at", complaint.resolution_due_at, complaint.resolved_at),
            ("follow_up_due_at", complaint.follow_up_due_at, None),
        ]
        for field_name, due_at, satisfied_at in milestones:
            if due_at is None or satisfied_at is not None:
                continue
            approaching_type, breached_type = SLA_EVENT_TYPES_BY_MILESTONE[field_name]
            event_type = breached_type if now >= due_at else None
            if event_type is None and due_at - now <= APPROACHING_THRESHOLD:
                event_type = approaching_type
            if event_type is None:
                continue

            dedup_key = _dedup_key(complaint.id, event_type)
            existing = await session.scalar(
                select(ComplaintSlaEvent.id).where(ComplaintSlaEvent.dedup_key == dedup_key)
            )
            if existing is not None:
                continue

            event = ComplaintSlaEvent(
                complaint_id=complaint.id,
                event_type=event_type,
                dedup_key=dedup_key,
            )
            session.add(event)
            created.append(event)

    if created:
        await session.flush()
    return created


# --- SLA policy CRUD ---------------------------------------------------------


async def get_sla_policy(session: AsyncSession, policy_id: uuid.UUID) -> SlaPolicy | None:
    return await session.get(SlaPolicy, policy_id)


async def list_sla_policies(
    session: AsyncSession, *, is_active: bool | None = None
) -> list[SlaPolicy]:
    query = select(SlaPolicy)
    if is_active is not None:
        query = query.where(SlaPolicy.is_active == is_active)
    result = await session.scalars(query.order_by(SlaPolicy.name))
    return list(result.all())


async def create_sla_policy(session: AsyncSession, *, payload: SlaPolicyCreateIn) -> SlaPolicy:
    policy = SlaPolicy(
        code=payload.code,
        name=payload.name,
        applicable_categories=payload.applicable_categories,
        applicable_severities=payload.applicable_severities,
        first_response_minutes=payload.first_response_minutes,
        acknowledgement_minutes=payload.acknowledgement_minutes,
        resolution_minutes=payload.resolution_minutes,
        follow_up_minutes=payload.follow_up_minutes,
        escalation_after_minutes=payload.escalation_after_minutes,
        business_hours_only=payload.business_hours_only,
        default_assignee_department_id=payload.default_assignee_department_id,
    )
    session.add(policy)
    await session.flush()
    return policy


async def update_sla_policy(
    session: AsyncSession, *, policy: SlaPolicy, payload: SlaPolicyUpdateIn
) -> SlaPolicy:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(policy, field, value)
    await session.flush()
    return policy
