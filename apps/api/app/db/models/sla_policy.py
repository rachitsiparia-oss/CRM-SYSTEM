import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# Instruction section 5.3. `applicable_categories`/`applicable_severities`
# are bounded JSONB arrays of already-CHECK-constrained enum codes (null
# means "applies to all") — a closed, small filter list, not the
# "unbounded JSON blob for core searchable business data" CLAUDE.md
# section 5.3 warns against; the complaint's own `category`/`severity`
# columns remain the actual searchable/filterable fields.


class SlaPolicy(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """No reusable "add N business hours, skipping closed periods"
    calculator exists anywhere in the codebase (confirmed absent from
    `app.reservations.availability`, the only other business-hours-aware
    module) — `app.complaints.sla.compute_due_at` is written fresh for this
    phase, but reads the existing Phase 9 `business_hours`/
    `holiday_calendar` tables as the single source of truth for operating
    hours rather than re-deriving them."""

    __tablename__ = "sla_policies"
    __table_args__ = (
        CheckConstraint("first_response_minutes > 0", name="valid_first_response_minutes"),
        CheckConstraint("acknowledgement_minutes > 0", name="valid_acknowledgement_minutes"),
        CheckConstraint("resolution_minutes > 0", name="valid_resolution_minutes"),
        CheckConstraint(
            "follow_up_minutes IS NULL OR follow_up_minutes > 0", name="valid_follow_up_minutes"
        ),
        CheckConstraint(
            "escalation_after_minutes IS NULL OR escalation_after_minutes > 0",
            name="valid_escalation_after_minutes",
        ),
    )

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    applicable_categories: Mapped[list[str] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    applicable_severities: Mapped[list[str] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    first_response_minutes: Mapped[int] = mapped_column(nullable=False)
    acknowledgement_minutes: Mapped[int] = mapped_column(nullable=False)
    resolution_minutes: Mapped[int] = mapped_column(nullable=False)
    follow_up_minutes: Mapped[int | None] = mapped_column(nullable=True)
    escalation_after_minutes: Mapped[int | None] = mapped_column(nullable=True)
    business_hours_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_assignee_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
