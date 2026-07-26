import uuid

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ProductVariant(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 8.3, CORE_CRM_MODULES.md section 7.6 —
    e.g. 8-inch/11-inch pizza sizes. `is_available` and
    `preparation_minutes` are this phase's own extensions beyond the
    documented column list ("own availability", "own preparation time
    (optional)"): `is_available` lets staff mark one size temporarily
    unorderable without touching the variant's own active/inactive state
    (same active-vs-available split `Product` already uses), and
    `preparation_minutes` overrides the parent product's prep time only
    when a size genuinely takes longer, staying NULL (inherit) otherwise.
    """

    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("price_minor >= 0", name="valid_price_minor"),
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        CheckConstraint(
            "preparation_minutes IS NULL OR preparation_minutes >= 0",
            name="valid_preparation_minutes",
        ),
        Index("ix_product_variants_product_id", "product_id"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    preparation_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
