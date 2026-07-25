import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class StaffRole(Base):
    """Staff-to-role assignment — DATABASE_AND_API.md section 4.5."""

    __tablename__ = "staff_roles"
    __table_args__ = (PrimaryKeyConstraint("staff_user_id", "role_id", name="pk_staff_roles"),)

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
