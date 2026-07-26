import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin

# This phase's own instruction: "NO payment gateway integration. Support
# recording only." References are external, staff-entered identifiers
# (e.g. a UPI transaction ID written on a receipt), never a gateway
# callback or webhook payload.
PAYMENT_METHODS = ("cash", "card", "upi", "online")
PAYMENT_RECORD_STATUSES = ("pending", "partial", "paid", "refunded", "failed")


class OrderPayment(UUIDPrimaryKeyMixin, Base):
    """This phase's own instruction: "Add payment / Update payment status /
    Partial payments / History" and "Store references only" (no gateway).
    Not built on AuditedMixin — `recorded_by` (required) plays that role
    more precisely than a nullable `created_by` would for a financial
    ledger row that must always name who entered it.
    """

    __tablename__ = "order_payments"
    __table_args__ = (
        CheckConstraint(f"method IN {PAYMENT_METHODS!r}", name="valid_method"),
        CheckConstraint(f"status IN {PAYMENT_RECORD_STATUSES!r}", name="valid_status"),
        CheckConstraint("amount_minor >= 0", name="valid_amount_minor"),
        Index("ix_order_payments_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
