import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin

# Not enumerated by this phase's instruction ("Charges" is named as a
# single order-level field); a small controlled set covering the
# charge kinds a fast-food restaurant actually applies, matching the
# closed-set-over-free-text pattern this project already uses for
# comparable small vocabularies (e.g. Product.spice_level).
ORDER_CHARGE_TYPES = ("packaging", "delivery", "service", "other")


class OrderCharge(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Itemized charge lines (packaging, delivery, service, etc.) summing
    to `Order.charges_minor` — same summary-column-plus-itemized-table
    pattern as order_discounts and order_taxes.
    """

    __tablename__ = "order_charges"
    __table_args__ = (
        CheckConstraint(f"charge_type IN {ORDER_CHARGE_TYPES!r}", name="valid_charge_type"),
        CheckConstraint("amount_minor >= 0", name="valid_amount_minor"),
        Index("ix_order_charges_order_id", "order_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    charge_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
