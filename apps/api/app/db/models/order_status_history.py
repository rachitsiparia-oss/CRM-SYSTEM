import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class OrderStatusHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only status-transition ledger — mirrors LeadStatusHistory.
    Distinct from OrderTimeline (the broader activity feed this phase's own
    instruction also names as a separate table); every status change is
    recorded in both, the same dual-write LeadStatusHistory/LeadActivity
    already establishes for leads.
    """

    __tablename__ = "order_status_history"
    __table_args__ = (Index("ix_order_status_history_order_id", "order_id"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
