import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin


class OrderNote(UUIDPrimaryKeyMixin, Base):
    """Structured, individually-timestamped note history for an order —
    mirrors CustomerNote's edit/soft-delete pattern
    (CORE_CRM_MODULES.md section 4.14's "do not allow silent note deletion,
    use soft deletion", the same treatment applied here). `is_internal`
    distinguishes staff-only notes from customer-facing ones, matching the
    `Order.internal_notes`/`Order.customer_notes` quick-glance summary
    fields this phase's own ORDER MODEL field list also requests — those
    two fields hold the current summary text; this table holds the full,
    attributable running history.
    """

    __tablename__ = "order_notes"
    __table_args__ = (Index("ix_order_notes_order_id", "order_id"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
