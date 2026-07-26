import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 6.4 lists only id/customer_id/note_type/
# content/is_sensitive/created_by/created_at. updated_at/updated_by/
# deleted_at/deleted_by are added during Phase 5 implementation because
# CORE_CRM_MODULES.md section 4.14 requires them ("editing a note should
# create revision history or be restricted to a short correction window...
# do not allow silent note deletion, use soft deletion").
NOTE_TYPES = (
    "general",
    "service_preference",
    "complaint",
    "recovery",
    "corporate",
    "delivery",
    "reservation",
    "dietary",
)


class CustomerNote(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "customer_notes"
    __table_args__ = (
        CheckConstraint(f"note_type IN {NOTE_TYPES!r}", name="valid_note_type"),
        Index("ix_customer_notes_customer_id", "customer_id"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    note_type: Mapped[str] = mapped_column(String(32), nullable=False, default="general")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
