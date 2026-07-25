import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 4.6 — added during Phase 3 implementation.
INVITATION_STATUSES = ("pending", "accepted", "revoked", "expired")


class StaffInvitation(UUIDPrimaryKeyMixin, Base):
    """CRM-level record of a staff invitation — DATABASE_AND_API.md section
    4.6. Tracks intended role/department and inviter; Supabase Auth owns the
    actual invite-token delivery and is not duplicated here.
    """

    __tablename__ = "staff_invitations"
    __table_args__ = (
        CheckConstraint(f"status IN {INVITATION_STATUSES!r}", name="valid_status"),
        Index("ix_staff_invitations_email", "email"),
    )

    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    intended_role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    invited_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    staff_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
