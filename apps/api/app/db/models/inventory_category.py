from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class InventoryCategory(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """A managed inventory-category catalogue.

    DATABASE_AND_API.md section 9.1 models this as a bare
    `category VARCHAR(64)` column on `inventory_items`. This phase's own
    instruction requires categories to be manageable records with a code,
    description, display order, active flag, and archive/restore — which a
    bare string cannot carry. Deliberately mirrors `MenuCategory`
    (Phase 6) so the two category systems stay recognizably the same shape
    while remaining separate: menu categories group *sellable products*,
    inventory categories group *stock-controlled materials*. See
    DATABASE_AND_API.md section 9.8 for the recorded deviation.
    """

    __tablename__ = "inventory_categories"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        Index(
            "ix_inventory_categories_active",
            "sort_order",
            postgresql_where=text("deleted_at IS NULL AND is_active"),
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
