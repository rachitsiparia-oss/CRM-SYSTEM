import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

SEGMENT_TYPES = ("dynamic", "static")
SEGMENT_STATUSES = ("draft", "active", "archived")


class Segment(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """GROWTH_AND_INTELLIGENCE.md section 4. `rule_definition` uses the same
    constrained, versioned condition schema as offers/achievements
    (section 6.6-6.7, `app.commercial_rules.schema`) — never arbitrary SQL.

    Dynamic segments are evaluated live for small operations
    (`app.segments.evaluate_membership`) and materialized into
    `segment_memberships` only on an explicit refresh
    (`refreshed_at`/`estimated_count` below). A campaign audience is always
    built from a snapshot (`Campaign.audience_snapshot`), never a live
    re-evaluation, so later segment edits cannot silently change history.
    """

    __tablename__ = "segments"
    __table_args__ = (
        CheckConstraint(f"segment_type IN {SEGMENT_TYPES!r}", name="valid_segment_type"),
        CheckConstraint(f"status IN {SEGMENT_STATUSES!r}", name="valid_status"),
        CheckConstraint("rule_version >= 1", name="valid_rule_version"),
        Index("ix_segments_status", "status"),
        Index("ix_segments_type", "segment_type"),
    )

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    segment_type: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="draft")
    # Constrained condition tree — validated against app.commercial_rules
    # at write time. NULL for a purely static segment.
    rule_definition: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    refresh_strategy: Mapped[str | None] = mapped_column(String(30), nullable=True)
    estimated_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_computed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    owner_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    is_seed_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


SEGMENT_MEMBERSHIP_ACTIONS = ("added", "removed")


class SegmentMembership(UUIDPrimaryKeyMixin, Base):
    """Immutable static-membership history — GROWTH_AND_INTELLIGENCE.md
    section 4.9: "Static membership must have immutable add/remove
    history." Current membership for a customer is the most recent row per
    (segment_id, customer_id) with `action = 'added'` and no later
    `'removed'` row — computed at read time, never mutated in place.
    """

    __tablename__ = "segment_memberships"
    __table_args__ = (
        CheckConstraint(f"action IN {SEGMENT_MEMBERSHIP_ACTIONS!r}", name="valid_action"),
        Index("ix_segment_memberships_segment_id", "segment_id"),
        Index("ix_segment_memberships_customer_id", "customer_id"),
        Index("ix_segment_memberships_segment_customer", "segment_id", "customer_id"),
    )

    segment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("segments.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    added_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
