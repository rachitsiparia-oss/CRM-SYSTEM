import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class OrderItemModifier(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Not one of the 11 tables this phase's instruction names explicitly,
    but required to store an order item's "Modifiers" field (also this
    phase's own instruction) as normalized, queryable rows rather than an
    unbounded JSON blob (CLAUDE.md section 5.3 forbids the latter for core
    searchable/relational business data) — the same normalization judgment
    call this phase's own instruction authorizes ("Only normalize where it
    actually improves the design"). Mirrors DATABASE_AND_API.md section
    10.3's own documented `order_item_modifiers` table. Snapshots the
    modifier name/price so later menu edits never alter historical orders,
    same reasoning as OrderItem's snapshot fields.
    """

    __tablename__ = "order_item_modifiers"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="valid_quantity"),
        CheckConstraint("price_minor_snapshot >= 0", name="valid_price_minor_snapshot"),
        Index("ix_order_item_modifiers_order_item_id", "order_item_id"),
    )

    order_item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("order_items.id"), nullable=False)
    modifier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("modifiers.id"), nullable=True)
    modifier_name_snapshot: Mapped[str] = mapped_column(String(120), nullable=False)
    price_minor_snapshot: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
