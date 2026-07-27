import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

BLOCK_TYPES = ("cleaning", "maintenance", "private_event", "other")


class TableBlock(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A time-bounded reason a table is unavailable for new reservations —
    consulted by the availability engine (`app.reservations.availability`)
    alongside posted reservations. Not soft-deletable: a block is either
    still active (`is_active=True`) or has run its course /
    was released early (`is_active=False`); the row itself is a permanent
    operational record, the same "closed, not deleted" treatment
    `StockCount`/`StockTransfer` give a finished document.
    """

    __tablename__ = "table_blocks"
    __table_args__ = (
        CheckConstraint(f"block_type IN {BLOCK_TYPES!r}", name="valid_block_type"),
        CheckConstraint("ends_at > starts_at", name="valid_time_window"),
        Index("ix_table_blocks_table_id", "restaurant_table_id"),
        Index(
            "ix_table_blocks_active_window",
            "restaurant_table_id",
            "starts_at",
            "ends_at",
        ),
    )

    restaurant_table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("restaurant_tables.id"), nullable=False
    )
    block_type: Mapped[str] = mapped_column(String(24), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    released_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
