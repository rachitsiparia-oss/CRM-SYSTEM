"""Campaign launch and delivery-status reconciliation —
GROWTH_AND_INTELLIGENCE.md section 3.13: "Each recipient execution has an
idempotency key", "Progress is based on stored recipient states, not
browser state." Reuses Phase 10's `ScheduledMessage`/
`process_due_scheduled_messages` engine end to end rather than a second
send pipeline — CLAUDE.md section 14's "engine, not scheduler" applies
here exactly as it did to reservation reminders.

No ARQ job triggers `launch`/`process_due_scheduled_messages` yet in this
codebase (only the Phase 4 heartbeat cron exists in `apps/worker`);
`launch` is therefore a staff-triggered, chunked batch operation here,
matching the same synchronous-but-bounded scoping already used for
`app.segments.membership.refresh`. Wiring an ARQ job to call
`process_due_scheduled_messages` on a schedule is unchanged future work,
not something this module works around.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.audit.service import record_audit_event
from app.campaigns.errors import CampaignError
from app.communications.consent import evaluate_send_eligibility
from app.db.models import (
    Campaign,
    CampaignRecipient,
    CommunicationChannel,
    Customer,
    ScheduledMessage,
    StaffUser,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_BATCH_SIZE = 200


def _destination_for(channel_code: str, customer: Customer) -> str | None:
    if channel_code == "email":
        return customer.primary_email
    if channel_code in ("sms", "whatsapp"):
        return customer.primary_phone_e164
    return None


async def launch(session: AsyncSession, *, campaign: Campaign, actor: StaffUser) -> tuple[int, int]:
    """Evaluates every `pending` recipient's send eligibility and queues a
    `ScheduledMessage` for each eligible one. Returns (queued, suppressed).
    Safe to call repeatedly — already-processed recipients (status !=
    'pending') are left untouched.
    """
    if campaign.status != "running":
        raise CampaignError(
            f"Campaign {campaign.code!r} is {campaign.status!r}; launch requires 'running'."
        )

    queued = 0
    suppressed = 0
    last_id: uuid.UUID | None = None
    scheduled_for = campaign.scheduled_at or datetime.now(UTC)

    while True:
        query = (
            select(CampaignRecipient)
            .where(
                CampaignRecipient.campaign_id == campaign.id, CampaignRecipient.status == "pending"
            )
            .order_by(CampaignRecipient.id)
            .limit(_BATCH_SIZE)
        )
        if last_id is not None:
            query = query.where(CampaignRecipient.id > last_id)
        batch = list(await session.scalars(query))
        if not batch:
            break

        for recipient in batch:
            channel = await session.get(CommunicationChannel, recipient.channel_id)
            customer = await session.get(Customer, recipient.customer_id)
            if channel is None or customer is None:
                recipient.status = "failed"
                recipient.failure_reason = "channel_or_customer_missing"
                recipient.failed_at = datetime.now(UTC)
                continue

            destination = _destination_for(channel.code, customer)
            eligibility = await evaluate_send_eligibility(
                session,
                channel=channel,
                destination_reference=destination,
                customer_id=customer.id,
                is_transactional=False,
            )
            if not eligibility.allowed:
                recipient.status = "suppressed"
                recipient.suppression_reason = eligibility.reason
                suppressed += 1
                continue

            template_id_raw = campaign.channel_templates.get(str(channel.id))
            scheduled = ScheduledMessage(
                id=uuid.uuid4(),
                purpose="campaign",
                template_id=uuid.UUID(template_id_raw) if template_id_raw else None,
                customer_id=customer.id,
                channel_id=channel.id,
                recipient_reference=destination or "",
                scheduled_for=scheduled_for,
                template_variables=None,
                status="scheduled",
                idempotency_key=f"campaign:{campaign.id}:{recipient.id}",
            )
            session.add(scheduled)
            await session.flush()
            recipient.scheduled_message_id = scheduled.id
            recipient.status = "eligible"
            queued += 1

        last_id = batch[-1].id
        await session.flush()
        if len(batch) < _BATCH_SIZE:
            break

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="campaign.launched",
        target_type="campaign",
        target_id=campaign.id,
        safe_metadata={"queued": queued, "suppressed": suppressed},
    )
    return queued, suppressed


async def sync_recipient_statuses(session: AsyncSession, *, campaign: Campaign) -> int:
    """Reconciles `eligible` recipients against their linked
    `ScheduledMessage`'s outcome — 'sent'/'failed' recipient states always
    come from the authoritative scheduled-message record, never guessed."""
    rows = await session.scalars(
        select(CampaignRecipient).where(
            CampaignRecipient.campaign_id == campaign.id,
            CampaignRecipient.status == "eligible",
            CampaignRecipient.scheduled_message_id.is_not(None),
        )
    )
    updated = 0
    for recipient in rows:
        scheduled = await session.get(ScheduledMessage, recipient.scheduled_message_id)
        if scheduled is None:
            continue
        if scheduled.status == "sent":
            recipient.status = "sent"
            recipient.message_id = scheduled.result_message_id
            recipient.sent_at = scheduled.updated_at
            updated += 1
        elif scheduled.status == "failed":
            recipient.status = "failed"
            recipient.failure_reason = scheduled.last_error
            recipient.failed_at = scheduled.updated_at
            updated += 1
    await session.flush()
    return updated


async def get_analytics(session: AsyncSession, *, campaign_id: uuid.UUID) -> dict[str, int]:
    rows = await session.execute(
        select(CampaignRecipient.status, func.count())
        .where(CampaignRecipient.campaign_id == campaign_id)
        .group_by(CampaignRecipient.status)
    )
    counts = {status: count for status, count in rows}
    return {
        "total_recipients": sum(counts.values()),
        "pending": counts.get("pending", 0),
        "eligible": counts.get("eligible", 0),
        "suppressed": counts.get("suppressed", 0),
        "sent": counts.get("sent", 0),
        "failed": counts.get("failed", 0),
    }
