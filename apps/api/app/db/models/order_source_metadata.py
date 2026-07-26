import uuid

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base


class OrderSourceMetadata(Base, AppendOnlyTimestampMixin):
    """One-to-one source-specific metadata for an order (e.g. a POS/Zomato/
    Swiggy external order ID for reconciliation), kept off the core
    `orders` table so per-source columns don't accumulate there as more
    sources gain real integrations later (CLAUDE.md section 16: no
    integration is claimed active without a verified API/export — this
    table only stores identifiers staff or a future adapter attach, never
    a fabricated payload). `order_id` is both primary key and foreign key
    since the relationship is strictly 1:1.
    """

    __tablename__ = "order_source_metadata"
    __table_args__ = (
        Index(
            "uq_order_source_metadata_external_order_id",
            "external_order_id",
            unique=True,
            postgresql_where=text("external_order_id IS NOT NULL"),
        ),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), primary_key=True)
    external_order_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_platform_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    reconciliation_note: Mapped[str | None] = mapped_column(Text, nullable=True)
