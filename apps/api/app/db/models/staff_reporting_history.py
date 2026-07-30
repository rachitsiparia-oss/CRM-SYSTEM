import uuid

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class StaffReportingHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only department/reporting-manager change ledger — this
    phase's own "Immutable operational history" principle, section 13
    ("Department history", "Staff transfer history")."""

    __tablename__ = "staff_reporting_history"
    __table_args__ = (Index("ix_staff_reporting_history_staff_user_id", "staff_user_id"),)

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    previous_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    new_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    previous_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    new_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
