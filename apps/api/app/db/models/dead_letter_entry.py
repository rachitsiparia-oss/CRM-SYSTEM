import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# INTEGRATIONS_AUTOMATIONS_REALTIME.md section 12.1 — `source_id` is a
# polymorphic reference (job_records.id or outbox_events.id, selected by
# `source_type`), the same pattern TaskRecord.related_type/
# ConversationLink.linked_type established in earlier phases — no FK,
# since a single dead-letter table intentionally spans two source tables.
DEAD_LETTER_SOURCE_TYPES = ("job", "outbox_event")
# Section 12.2, verbatim.
DEAD_LETTER_STATUSES = (
    "new",
    "investigating",
    "corrected",
    "replay_ready",
    "replayed",
    "ignored_with_reason",
    "permanently_closed",
)


class DeadLetterEntry(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A job or outbox event that exhausted its retry budget —
    INTEGRATIONS_AUTOMATIONS_REALTIME.md section 12. Created by
    `app.jobs`/the outbox dispatcher when a `job_records`/`outbox_events`
    row reaches `failed_permanent`/`dead_lettered`; replay requires a
    human decision (`resolution_status` reaching `replay_ready`) — never
    an automatic re-run, per section 12.3's "Replay requires... permission
    ... confirmation that idempotency remains safe.\""""

    __tablename__ = "dead_letter_entries"
    __table_args__ = (
        CheckConstraint(f"source_type IN {DEAD_LETTER_SOURCE_TYPES!r}", name="valid_source_type"),
        CheckConstraint(
            f"resolution_status IN {DEAD_LETTER_STATUSES!r}", name="valid_resolution_status"
        ),
        Index("ix_dead_letter_entries_source", "source_type", "source_id"),
        Index("ix_dead_letter_entries_resolution_status", "resolution_status"),
    )

    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    original_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_reference: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    final_error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_history: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    dead_letter_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    owner_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    resolution_status: Mapped[str] = mapped_column(String(24), nullable=False, default="new")
    replay_eligible: Mapped[bool] = mapped_column(nullable=False, default=False)
    replay_actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    replay_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
