import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

REQUEST_TYPES = ("swap", "cover", "change")
REQUEST_STATUSES = ("pending", "approved", "rejected", "cancelled")


class ShiftChangeRequest(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """This phase's own instruction section 18. Whether `proposed_staff_id`
    is active/eligible is validated in `app.staff_operations.shifts`, not
    by a database constraint (eligibility depends on live employment
    lifecycle state, not something a CHECK constraint alone can express)."""

    __tablename__ = "shift_change_requests"
    __table_args__ = (
        CheckConstraint(f"request_type IN {REQUEST_TYPES!r}", name="valid_request_type"),
        CheckConstraint(f"status IN {REQUEST_STATUSES!r}", name="valid_status"),
        Index("ix_shift_change_requests_shift_id", "shift_id"),
    )

    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_shifts.id"), nullable=False)
    requested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    request_type: Mapped[str] = mapped_column(String(16), nullable=False)
    proposed_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
