import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

# This phase's own instruction: "Flat, Percentage, Manual, Coupon
# Placeholder, Manager Override."
ORDER_DISCOUNT_TYPES = ("flat", "percentage", "manual", "coupon_placeholder", "manager_override")


class OrderDiscount(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """This phase's own instruction: "store: Reason, Approved By,
    Timestamp." Itemized discount lines summing to `Order.discount_minor` —
    same summary-column-plus-itemized-table pattern as order_taxes and
    order_charges. `percentage` is the input basis for percentage-type
    discounts; `amount_minor` is always the computed, applied amount in
    minor units (CLAUDE.md's money architecture is non-negotiable
    regardless of discount type).
    """

    __tablename__ = "order_discounts"
    __table_args__ = (
        CheckConstraint(f"discount_type IN {ORDER_DISCOUNT_TYPES!r}", name="valid_discount_type"),
        CheckConstraint("amount_minor >= 0", name="valid_amount_minor"),
        CheckConstraint(
            "percentage IS NULL OR (percentage >= 0 AND percentage <= 100)",
            name="valid_percentage",
        ),
        Index("ix_order_discounts_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    approved_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
