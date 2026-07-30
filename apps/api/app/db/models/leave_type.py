from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LeaveType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """This phase's own instruction section 20 catalogue. No payroll
    accrual engine — `allows_carry_forward`/`carry_forward_max_days` are
    metadata only, per this phase's own instruction not to build "complex
    payroll accrual" or statutory processing."""

    __tablename__ = "leave_types"

    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_notice_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_consecutive_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allows_carry_forward: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    carry_forward_max_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
