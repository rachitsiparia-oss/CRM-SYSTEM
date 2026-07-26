from sqlalchemy import BigInteger, Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class Modifier(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 8.5 — a reusable modifier option catalog
    (e.g. "Cheese slice", "Jalapeños"), independent of any one group so the
    same option can be offered inside multiple modifier groups via
    `modifier_group_items` (section 8.6). `default_price_minor` is the
    price used unless a specific group mapping overrides it."""

    __tablename__ = "modifiers"
    __table_args__ = (CheckConstraint("default_price_minor >= 0", name="valid_default_price"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    default_price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
