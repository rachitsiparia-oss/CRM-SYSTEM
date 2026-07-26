import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# This phase's own instruction: each item stores "Status" but does not
# describe kitchen-stage granularity, and CLAUDE.md's own Phase 7 "DO NOT
# BUILD" list forbids kitchen display / preparation-stage workflows. Kept
# to whether the line is still part of the order, not a per-item kitchen
# stage.
ORDER_ITEM_STATUSES = ("active", "cancelled")


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """This phase's own ORDER ITEMS field list. Snapshots product/variant
    name and unit price at order time so later menu edits never alter
    historical orders (this phase's own instruction) — `product_id`/
    `variant_id` stay as references for reporting and re-order convenience
    only, never re-read for pricing after creation.
    """

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint(f"status IN {ORDER_ITEM_STATUSES!r}", name="valid_status"),
        CheckConstraint("quantity > 0", name="valid_quantity"),
        CheckConstraint("unit_price_minor >= 0", name="valid_unit_price_minor"),
        CheckConstraint("discount_minor >= 0", name="valid_discount_minor"),
        CheckConstraint("tax_minor >= 0", name="valid_tax_minor"),
        CheckConstraint("final_price_minor >= 0", name="valid_final_price_minor"),
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_product_id", "product_id"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product_variants.id"), nullable=True
    )
    product_name_snapshot: Mapped[str] = mapped_column(String(180), nullable=False)
    variant_name_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    product_code_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tax_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    final_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kitchen_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
