from sqlalchemy import Boolean, CheckConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class Permission(UUIDPrimaryKeyMixin, Base):
    """The single canonical capability registry — DATABASE_AND_API.md
    section 4.4. Rows are synchronized from `app.permissions.registry`,
    the one source of truth for permission codes; this table is never
    hand-edited.

    No timestamp columns: section 4.4 lists exactly `id`, `code`, `module`,
    `action`, `description`, `is_sensitive` and nothing else.
    """

    __tablename__ = "permissions"
    __table_args__ = (CheckConstraint("code = lower(code)", name="lowercase_code"),)

    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
