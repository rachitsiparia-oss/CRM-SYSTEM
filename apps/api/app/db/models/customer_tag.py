import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class CustomerTag(Base):
    """DATABASE_AND_API.md section 6.5 — customer-to-tag mapping."""

    __tablename__ = "customer_tags"
    __table_args__ = (PrimaryKeyConstraint("customer_id", "tag_id", name="pk_customer_tags"),)

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    tag_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tags.id"), nullable=False)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
