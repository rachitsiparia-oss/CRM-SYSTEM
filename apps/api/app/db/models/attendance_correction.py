import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin
from app.db.models.attendance_record import APPROVAL_STATES


class AttendanceCorrection(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Immutable correction-event ledger — "Do not silently overwrite
    historical facts" (this phase's own instruction section 3).
    `previous_values`/`new_values` snapshot the mutable fields of
    `AttendanceRecord` (status, times, minutes) at correction time."""

    __tablename__ = "attendance_corrections"
    __table_args__ = (
        CheckConstraint(f"approval_state IN {APPROVAL_STATES!r}", name="valid_approval_state"),
        Index("ix_attendance_corrections_attendance_record_id", "attendance_record_id"),
    )

    attendance_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_records.id"), nullable=False
    )
    previous_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    new_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    approval_state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
