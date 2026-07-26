import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ProductModifierGroup(Base):
    """Product-to-modifier-group mapping — DATABASE_AND_API.md section 8.6.
    Composite-key join table, same convention as `StaffRole`/`RolePermission`
    from Phase 3 and `CustomerTag` from Phase 5 — no surrogate id needed
    since the API addresses a mapping by its natural (product_id,
    modifier_group_id) pair."""

    __tablename__ = "product_modifier_groups"
    __table_args__ = (
        PrimaryKeyConstraint("product_id", "modifier_group_id", name="pk_product_modifier_groups"),
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    modifier_group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modifier_groups.id"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
