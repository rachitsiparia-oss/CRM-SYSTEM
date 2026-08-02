"""Multi-channel notification delivery —
INTEGRATIONS_AUTOMATIONS_REALTIME.md section 17. `app.notifications.service.notify()`
only ever creates the in-app `Notification` row; this module is what
actually sends the non-in-app channels a caller requested via
`delivery_channels`. Sent through
`app.communications.providers.get_provider()` (the same abstraction Phase
10 built for customer messaging — currently the deterministic mock
provider, since no real WhatsApp/email/SMS account is configured yet),
addressed directly to the staff member's own `email`/`phone_e164` rather
than through a `Conversation`/`CommunicationChannel` (those model
customer-facing conversations, a mismatch for a one-off internal alert).

Batching: one dispatch call processes up to `batch_size` notifications.
Throttling: the scheduler (`apps/worker`) controls how often this runs.
Retries: a channel gets up to `_MAX_ATTEMPTS_PER_CHANNEL` attempts, each
recorded as its own `NotificationDeliveryAttempt` row (never overwritten,
matching `MessageDeliveryAttempt`'s append-per-attempt shape); a channel
already `sent`/`delivered`/`skipped` is never re-attempted. Deduplication:
inherited for free from `Notification.dedup_key` — a duplicate
notification is never created, so there is nothing to double-deliver.
"""

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.communications.providers import get_provider
from app.core.logging import get_logger
from app.db.models import Notification, NotificationDeliveryAttempt, StaffUser

logger = get_logger(__name__)

_MAX_ATTEMPTS_PER_CHANNEL = 3
_TERMINAL_STATUSES = ("sent", "delivered", "skipped")


def _resolve_destination(staff: StaffUser, channel: str) -> str | None:
    if channel == "email":
        return staff.email
    if channel in ("whatsapp", "sms"):
        return staff.phone_e164
    return None  # "push" has no provider adapter yet — always skipped


async def dispatch_pending_notification_deliveries(
    session: AsyncSession, *, batch_size: int = 50
) -> dict[str, int]:
    candidates = (
        await session.scalars(
            select(Notification)
            .where(Notification.delivery_channels.isnot(None))
            .order_by(Notification.created_at)
            .limit(batch_size)
        )
    ).all()

    counts = {"sent": 0, "failed": 0, "skipped": 0}
    for notification in candidates:
        channels = [c for c in (notification.delivery_channels or []) if c != "in_app"]
        if not channels:
            continue

        attempts = (
            await session.scalars(
                select(NotificationDeliveryAttempt).where(
                    NotificationDeliveryAttempt.notification_id == notification.id
                )
            )
        ).all()
        attempts_by_channel: dict[str, list[NotificationDeliveryAttempt]] = defaultdict(list)
        for attempt in attempts:
            attempts_by_channel[attempt.channel].append(attempt)

        staff = await session.get(StaffUser, notification.recipient_staff_id)

        for channel in channels:
            channel_attempts = attempts_by_channel.get(channel, [])
            if any(a.status in _TERMINAL_STATUSES for a in channel_attempts):
                continue
            if len(channel_attempts) >= _MAX_ATTEMPTS_PER_CHANNEL:
                continue
            outcome = await _send_one(
                session, notification=notification, staff=staff, channel=channel
            )
            counts[outcome] = counts.get(outcome, 0) + 1
    return counts


async def _send_one(
    session: AsyncSession, *, notification: Notification, staff: StaffUser | None, channel: str
) -> str:
    attempt = NotificationDeliveryAttempt(
        notification_id=notification.id, channel=channel, status="pending"
    )
    session.add(attempt)

    destination = _resolve_destination(staff, channel) if staff is not None else None
    if destination is None:
        attempt.status = "skipped"
        attempt.error_message = (
            "Recipient has no destination on file for this channel."
            if staff is not None
            else "Recipient staff record no longer exists."
        )
        await session.flush()
        await session.commit()
        logger.info(
            "notification_delivery_skipped",
            notification_id=str(notification.id),
            channel=channel,
        )
        return "skipped"

    attempt.attempted_at = datetime.now(UTC)
    provider = get_provider(None)
    try:
        result = await provider.send_text(
            recipient_reference=destination, body=notification.body or notification.title
        )
    except Exception as exc:
        attempt.status = "failed"
        attempt.error_message = str(exc)[:2000]
        await session.flush()
        await session.commit()
        logger.warning(
            "notification_delivery_failed",
            notification_id=str(notification.id),
            channel=channel,
            error=str(exc),
        )
        return "failed"

    if result.accepted:
        attempt.status = "sent"
        attempt.provider_reference = result.provider_message_id
        outcome = "sent"
    else:
        attempt.status = "failed"
        attempt.error_message = result.failure_reason
        outcome = "failed"
    await session.flush()
    await session.commit()
    logger.info(
        "notification_delivery_attempted",
        notification_id=str(notification.id),
        channel=channel,
        outcome=outcome,
    )
    return outcome
