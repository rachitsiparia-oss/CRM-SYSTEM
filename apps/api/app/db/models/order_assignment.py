import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin


class OrderAssignment(UUIDPrimaryKeyMixin, Base):
    """Append-oriented staff-assignment history — `Order.assigned_staff_id`
    stays the fast "who is on it now" pointer (this phase's own ORDER
    MODEL field list), while this table preserves the full assignment
    history, the same fast-pointer-plus-history-table split
    CustomerMergeEvent already established for customer merges.
    """

    __tablename__ = "order_assignments"
    __table_args__ = (Index("ix_order_assignments_order_id", "order_id"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
