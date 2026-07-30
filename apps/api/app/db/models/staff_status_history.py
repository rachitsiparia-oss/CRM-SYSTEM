import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class StaffStatusHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only `StaffEmploymentProfile.lifecycle_status` transition
    ledger — this phase's own "Immutable operational history" principle,
    mirrors `ReservationStatusHistory`."""

    __tablename__ = "staff_status_history"
    __table_args__ = (Index("ix_staff_status_history_staff_user_id", "staff_user_id"),)

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    new_status: Mapped[str] = mapped_column(String(24), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
