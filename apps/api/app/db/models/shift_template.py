import uuid
from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


class ShiftTemplate(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """DATABASE_AND_API.md section 14.5 sketch, elaborated per this phase's
    own instruction section 17. Overlap and overnight-shift validation
    happens in `app.staff_operations.shifts` against `StaffShift` rows, not
    here — a template is just a reusable definition, never itself
    scheduled."""

    __tablename__ = "shift_templates"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_overnight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grace_period_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
