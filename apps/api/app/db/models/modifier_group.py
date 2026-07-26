from sqlalchemy import Boolean, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class ModifierGroup(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 8.4 — e.g. "Add-ons", "Spice Level".
    `sort_order` is this phase's own extension ("display order" in this
    phase's own feature list, not in the documented column set)."""

    __tablename__ = "modifier_groups"
    __table_args__ = (
        CheckConstraint("min_select >= 0", name="valid_min_select"),
        CheckConstraint("max_select >= 1", name="valid_max_select"),
        CheckConstraint("max_select >= min_select", name="max_select_at_least_min_select"),
        CheckConstraint("sort_order >= 0", name="valid_sort_order"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    min_select: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_select: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
