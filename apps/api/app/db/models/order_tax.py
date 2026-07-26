import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class OrderTax(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Itemized tax lines (e.g. "GST 5%") summing to `Order.tax_minor` —
    same summary-column-plus-itemized-table pattern as order_discounts and
    order_charges.
    """

    __tablename__ = "order_taxes"
    __table_args__ = (
        CheckConstraint("amount_minor >= 0", name="valid_amount_minor"),
        CheckConstraint(
            "rate_percentage IS NULL OR (rate_percentage >= 0 AND rate_percentage <= 100)",
            name="valid_rate_percentage",
        ),
        Index("ix_order_taxes_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    tax_name: Mapped[str] = mapped_column(String(64), nullable=False)
    rate_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
