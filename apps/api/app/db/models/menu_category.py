from sqlalchemy import Boolean, CheckConstraint, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class MenuCategory(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 8.1, CORE_CRM_MODULES.md section 7.2.

    Flat categories only — nested (parent_category_id) and category images
    are both absent from every canonical document, and this phase's own
    instruction says to add nested categories "if already described in
    documentation," which it is not. Both are left for an explicit future
    decision rather than invented here.
    """

    __tablename__ = "menu_categories"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        Index(
            "ix_menu_categories_active",
            "sort_order",
            postgresql_where=text("deleted_at IS NULL AND is_active"),
        ),
    )

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
