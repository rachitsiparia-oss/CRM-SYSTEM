import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ModifierGroupItem(Base):
    """Modifier-to-group mapping — DATABASE_AND_API.md section 8.6. The
    same modifier (e.g. "Extra sauce") can appear in more than one group,
    each with its own sort order, availability, and optional price
    override — `price_minor_override` NULL means "use the modifier's own
    `default_price_minor`". Channel-specific pricing (also mentioned in
    section 8.6 as optional) is deferred: no ordering channel exists until
    Phase 7."""

    __tablename__ = "modifier_group_items"
    __table_args__ = (
        PrimaryKeyConstraint("modifier_group_id", "modifier_id", name="pk_modifier_group_items"),
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
        CheckConstraint(
            "price_minor_override IS NULL OR price_minor_override >= 0",
            name="valid_price_minor_override",
        ),
    )

    modifier_group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("modifier_groups.id"), nullable=False
    )
    modifier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("modifiers.id"), nullable=False)
    price_minor_override: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
