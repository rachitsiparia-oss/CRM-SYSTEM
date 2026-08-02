"""Tests for `app.notifications.dispatch` — multi-channel delivery of
notifications that requested `delivery_channels` beyond the in-app row
(INTEGRATIONS_AUTOMATIONS_REALTIME.md section 17)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.db.models import NotificationDeliveryAttempt, StaffUser
from app.notifications.dispatch import dispatch_pending_notification_deliveries
from app.notifications.service import notify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def test_dispatch_sends_email_channel_for_staff_with_email(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    recipient = await make_staff_user()  # factory always sets an email
    notification = await notify(
        db_session,
        notification_type="test.dispatch_email",
        title="Test notification",
        recipient_staff_id=recipient.id,
        delivery_channels=["email"],
    )
    assert notification is not None

    counts = await dispatch_pending_notification_deliveries(db_session)
    assert counts["sent"] >= 1

    attempt = await db_session.scalar(
        select(NotificationDeliveryAttempt).where(
            NotificationDeliveryAttempt.notification_id == notification.id
        )
    )
    assert attempt is not None
    assert attempt.channel == "email"
    assert attempt.status == "sent"
    assert attempt.provider_reference is not None


async def test_dispatch_skips_push_channel_with_no_provider(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    recipient = await make_staff_user()
    notification = await notify(
        db_session,
        notification_type="test.dispatch_push",
        title="Test notification",
        recipient_staff_id=recipient.id,
        delivery_channels=["push"],
    )
    assert notification is not None

    await dispatch_pending_notification_deliveries(db_session)

    attempt = await db_session.scalar(
        select(NotificationDeliveryAttempt).where(
            NotificationDeliveryAttempt.notification_id == notification.id
        )
    )
    assert attempt is not None
    assert attempt.status == "skipped"


async def test_dispatch_never_re_attempts_a_terminal_channel(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    recipient = await make_staff_user()
    notification = await notify(
        db_session,
        notification_type="test.dispatch_no_double_send",
        title="Test notification",
        recipient_staff_id=recipient.id,
        delivery_channels=["email"],
    )
    assert notification is not None

    first_counts = await dispatch_pending_notification_deliveries(db_session)
    await dispatch_pending_notification_deliveries(db_session)

    assert first_counts["sent"] >= 1
    attempts = (
        await db_session.scalars(
            select(NotificationDeliveryAttempt).where(
                NotificationDeliveryAttempt.notification_id == notification.id
            )
        )
    ).all()
    assert len(attempts) == 1  # never re-attempted a channel already `sent`
