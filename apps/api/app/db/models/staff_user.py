import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

# DATABASE_AND_API.md section 4.1, reconciled with SECURITY_PERFORMANCE_AND_QUALITY.md
# section 3.6 to include `archived` (fixed during Phase 3 — see docs changelog note
# in DATABASE_AND_API.md section 4.1).
ACCOUNT_STATUSES = ("invited", "active", "suspended", "disabled", "locked", "archived")

# Not enumerated in DATABASE_AND_API.md section 4.1; added during Phase 3 implementation.
EMPLOYMENT_STATUSES = ("full_time", "part_time", "contract", "intern")

# Account states that must not receive active CRM access —
# SECURITY_PERFORMANCE_AND_QUALITY.md section 3.6.
INACTIVE_ACCOUNT_STATUSES = ("suspended", "disabled", "locked", "archived")


class StaffUser(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """Internal CRM user profile mapped to a Supabase Auth identity —
    DATABASE_AND_API.md section 4.1.
    """

    __tablename__ = "staff_users"
    __table_args__ = (
        CheckConstraint(f"account_status IN {ACCOUNT_STATUSES!r}", name="valid_account_status"),
        CheckConstraint(
            f"employment_status IN {EMPLOYMENT_STATUSES!r}", name="valid_employment_status"
        ),
        Index("ix_staff_users_department_id", "department_id"),
        Index(
            "uq_staff_users_active_email",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_staff_users_active",
            "account_status",
            postgresql_where=text("account_status = 'active' AND deleted_at IS NULL"),
        ),
    )

    auth_user_id: Mapped[uuid.UUID] = mapped_column(unique=True, nullable=False)
    employee_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    phone_e164: Mapped[str | None] = mapped_column(String(20), nullable=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    job_title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_status: Mapped[str] = mapped_column(String(32), nullable=False, default="invited")
    employment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="full_time")
    is_privileged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    avatar_storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
