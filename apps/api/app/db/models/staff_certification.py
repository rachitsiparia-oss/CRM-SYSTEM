import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

VERIFICATION_STATUSES = ("pending", "verified", "rejected", "expired")


class StaffCertification(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """This phase's own instruction section 23. `renewal_of_certification_id`
    links a renewed certificate back to the one it replaces, without
    deleting the expired row's history."""

    __tablename__ = "staff_certifications"
    __table_args__ = (
        CheckConstraint(
            f"verification_status IN {VERIFICATION_STATUSES!r}", name="valid_verification_status"
        ),
        CheckConstraint(
            "expiry_date IS NULL OR expiry_date >= issue_date", name="valid_expiry_after_issue"
        ),
        Index("ix_staff_certifications_staff_user_id", "staff_user_id"),
        Index("ix_staff_certifications_expiry_date", "expiry_date"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    certification_type: Mapped[str] = mapped_column(String(120), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(160), nullable=True)
    certificate_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(String(80), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    renewal_of_certification_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_certifications.id"), nullable=True
    )
