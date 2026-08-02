"""Reservation reminder dispatch — the engine function
`ReservationSettings.reminder_lead_time_minutes` and the `reminder_scheduled`
status were both anticipated in Phase 9 but never wired to anything before
this phase (`reminder_lead_time_minutes` was read nowhere in the codebase;
nothing ever created a `reservation_reminder` scheduled message). Reuses
Phase 10's `ScheduledMessage`/`process_due_scheduled_messages` engine for
the actual send — no second send pipeline — and Phase 13's
`_CHANNEL_CODE_TO_FIELD`/`evaluate_send_eligibility` pattern
(`app.feedback.review_requests`) for channel/consent resolution, applied
to a guest's own `Reservation.phone_e164`/`.email` rather than a
`Customer` (a reservation is not required to have a linked customer).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.consent import evaluate_send_eligibility
from app.core.system_actor import get_system_actor
from app.db.models import CommunicationChannel, Reservation, ReservationSettings, ScheduledMessage
from app.reservations.service import transition_reservation

_CHANNEL_CODE_TO_RESERVATION_FIELD = {
    "whatsapp": "phone_e164",
    "sms": "phone_e164",
    "email": "email",
}


async def dispatch_reservation_reminders(
    session: AsyncSession, *, now: datetime | None = None
) -> int:
    now = now or datetime.now(UTC)
    settings = await session.scalar(select(ReservationSettings).limit(1))
    lead_minutes = settings.reminder_lead_time_minutes if settings else None
    if not lead_minutes:
        return 0

    system_actor = await get_system_actor(session)
    if system_actor is None:
        return 0

    candidates = (
        await session.scalars(
            select(Reservation).where(
                Reservation.status == "confirmed",
                Reservation.reservation_date == now.date(),
            )
        )
    ).all()

    dispatched = 0
    for reservation in candidates:
        start_dt = datetime.combine(
            reservation.reservation_date, reservation.start_time, tzinfo=now.tzinfo
        )
        if now < start_dt - timedelta(minutes=lead_minutes) or now >= start_dt:
            continue

        for channel_code, field in _CHANNEL_CODE_TO_RESERVATION_FIELD.items():
            destination = getattr(reservation, field, None)
            if not destination:
                continue
            channel = await session.scalar(
                select(CommunicationChannel).where(CommunicationChannel.code == channel_code)
            )
            if channel is None:
                continue
            eligibility = await evaluate_send_eligibility(
                session,
                channel=channel,
                destination_reference=destination,
                customer_id=reservation.customer_id,
                is_transactional=True,
            )
            if not eligibility.allowed:
                continue

            message = ScheduledMessage(
                purpose="reservation_reminder",
                customer_id=reservation.customer_id,
                channel_id=channel.id,
                recipient_reference=destination,
                scheduled_for=now,
                status="scheduled",
                idempotency_key=f"reservation-reminder:{reservation.id}",
            )
            session.add(message)
            await session.flush()
            await transition_reservation(
                session,
                actor=system_actor,
                reservation=reservation,
                new_status="reminder_scheduled",
                reason="Automatic reminder scheduled.",
                request=None,
            )
            dispatched += 1
            break
    return dispatched
