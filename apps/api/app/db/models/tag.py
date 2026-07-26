from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Tag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """DATABASE_AND_API.md section 6.5. `normalized_name` (lowercase,
    whitespace-collapsed via app.customers.normalization) carries the
    uniqueness constraint so tags differing only by case or whitespace
    can't be created twice — this phase's own duplicate-tag requirement."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
