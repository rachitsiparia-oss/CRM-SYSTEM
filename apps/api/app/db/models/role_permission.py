import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, PrimaryKeyConstraint, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base

SCOPE_TYPES = ("all", "department", "assigned", "self", "none")


class RolePermission(Base):
    """Role-to-permission grant — DATABASE_AND_API.md section 4.5."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        PrimaryKeyConstraint("role_id", "permission_id", name="pk_role_permissions"),
        CheckConstraint(f"scope_type IN {SCOPE_TYPES!r}", name="valid_scope_type"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    permission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("permissions.id"), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, default="all")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
