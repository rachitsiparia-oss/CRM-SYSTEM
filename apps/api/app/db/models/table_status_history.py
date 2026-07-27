import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class TableStatusHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only table-status change log — the history half of
    `RestaurantTable.status`'s fast-pointer-plus-history split. Also
    records merge/split events (see `restaurant_table.py`'s own docstring
    for why "merged"/"split" are not both persistent status values):
    `reason` carries free text such as "merged with T-12" or "split from
    T-12" for those events, matched against `event_metadata` for the
    paired table id.
    """

    __tablename__ = "table_status_history"
    __table_args__ = (Index("ix_table_status_history_table_id", "restaurant_table_id"),)

    restaurant_table_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("restaurant_tables.id"), nullable=False
    )
    previous_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    new_status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
