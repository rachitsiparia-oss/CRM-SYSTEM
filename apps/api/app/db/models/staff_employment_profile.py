import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# Deliberately distinct from two existing `staff_users` columns this phase
# does NOT touch: `staff_users.account_status` already is the "system
# access status" PROJECT_PLAN.md asks to keep separate (invited/active/
# suspended/disabled/locked/archived), and `staff_users.employment_status`
# is actually an employment *type* (full_time/part_time/contract/intern)
# despite its name — a Phase 3 naming choice this phase does not rename to
# avoid an unrelated breaking migration. `lifecycle_status` here is the
# new concept this phase's own instruction names: where a person actually
# is in the employment journey.
LIFECYCLE_STATUSES = (
    "invited",
    "onboarding",
    "active",
    "on_leave",
    "suspended",
    "notice_period",
    "inactive",
    "terminated",
)


class StaffEmploymentProfile(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """One-to-one extension of `staff_users` — DATABASE_AND_API.md section
    14.1's `staff_profiles` sketch, renamed to avoid colliding with the
    unrelated `CustomerPreference`-style `staff_profiles` term used
    nowhere else in code. Sensitive fields here (address, emergency
    contact, restricted notes) are gated by the existing
    `staff.hr_sensitive.read` permission (Phase 3) — not a new duplicate
    permission code."""

    __tablename__ = "staff_employment_profiles"
    __table_args__ = (
        CheckConstraint(
            f"lifecycle_status IN {LIFECYCLE_STATUSES!r}", name="valid_lifecycle_status"
        ),
        CheckConstraint(
            "reporting_manager_id IS NULL OR reporting_manager_id != staff_user_id",
            name="no_self_report",
        ),
        Index("ix_staff_employment_profiles_reporting_manager_id", "reporting_manager_id"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_users.id"), unique=True, nullable=False
    )
    lifecycle_status: Mapped[str] = mapped_column(String(24), nullable=False, default="invited")
    reporting_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    secondary_supervisor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    work_location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    default_shift_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shift_templates.id"), nullable=True
    )
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    probation_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_working_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    emergency_contact_relation: Mapped[str | None] = mapped_column(String(60), nullable=True)
    address_line1: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_postal_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    uniform_size: Mapped[str | None] = mapped_column(String(16), nullable=True)
    restricted_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
