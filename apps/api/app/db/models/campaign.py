import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 3.3 (unchanged from Phase 10's
# canonical campaign-status vocabulary — this table replaces no existing
# one, Phase 10 built conversations/tasks/notifications, not campaigns).
CAMPAIGN_STATUSES = (
    "draft",
    "ready",
    "scheduled",
    "running",
    "paused",
    "completed",
    "cancelled",
    "failed",
    "archived",
)


class Campaign(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Reuses the existing Phase 10 Communication Hub end to end —
    `channel_ids`/`template_ids` reference `communication_channels`/
    `message_templates` rather than a new provider layer
    (GROWTH_AND_INTELLIGENCE.md section 3, this phase's own instruction:
    "No live provider integration is required").

    `audience_snapshot_taken_at` marks when `CampaignRecipient` rows were
    materialized from the target segment(s) — the audience is always frozen
    at that moment, per `Segment`'s own docstring: "later segment changes
    [do not] alter historical campaign audiences."
    """

    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint(f"status IN {CAMPAIGN_STATUSES!r}", name="valid_status"),
        Index("ix_campaigns_status", "status"),
        Index("ix_campaigns_scheduled_at", "scheduled_at"),
    )

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    objective: Mapped[str | None] = mapped_column(String(60), nullable=True)
    campaign_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="draft")
    # {channel_id: template_id} — one template per channel this campaign uses.
    channel_templates: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    target_segment_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    excluded_segment_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    linked_offer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("offers.id"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    send_window_start_local: Mapped[str | None] = mapped_column(String(5), nullable=True)
    send_window_end_local: Mapped[str | None] = mapped_column(String(5), nullable=True)
    audience_snapshot_taken_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estimated_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    owner_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


CAMPAIGN_RECIPIENT_STATUSES = ("pending", "eligible", "suppressed", "sent", "failed")


class CampaignRecipient(UUIDPrimaryKeyMixin, Base):
    """One row per (campaign, customer, channel) — the frozen audience
    snapshot. `message_id`/`scheduled_message_id` link to the real Phase 10
    send record; this table never fabricates delivery/open/click state for
    a provider that cannot report it (this phase's own rule).
    """

    __tablename__ = "campaign_recipients"
    __table_args__ = (
        CheckConstraint(f"status IN {CAMPAIGN_RECIPIENT_STATUSES!r}", name="valid_status"),
        CheckConstraint("attempt_count >= 0", name="valid_attempt_count"),
        Index("ix_campaign_recipients_campaign_id", "campaign_id"),
        Index("ix_campaign_recipients_customer_id", "customer_id"),
        Index("ix_campaign_recipients_status", "status"),
        # A customer is targeted at most once per campaign per channel —
        # this phase's own "campaign audience deduplication" requirement.
        Index(
            "uq_campaign_recipients_campaign_customer_channel",
            "campaign_id",
            "customer_id",
            "channel_id",
            unique=True,
        ),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("communication_channels.id"), nullable=False
    )
    source_segment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("segments.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="pending")
    eligibility_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suppression_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    scheduled_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scheduled_messages.id"), nullable=True
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
