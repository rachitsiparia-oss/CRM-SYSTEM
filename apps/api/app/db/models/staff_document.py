import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

DOCUMENT_TYPES = (
    "identity_proof",
    "address_proof",
    "offer_letter",
    "employment_contract",
    "policy_acknowledgement",
    "food_safety_certificate",
    "medical_fitness_certificate",
    "training_certificate",
    "experience_letter",
    "exit_document",
    "other",
)
VERIFICATION_STATUSES = ("pending", "verified", "rejected", "expired")
UPLOAD_STATUSES = ("pending", "uploaded", "failed")
SCAN_STATUSES = ("pending", "clean", "infected", "skipped")


class StaffDocument(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """Private HR/operational document metadata — this phase's own
    instruction section 14. Gated by the existing `staff.hr_sensitive.read`
    permission (Phase 3), never exposed to the general staff directory."""

    __tablename__ = "staff_documents"
    __table_args__ = (
        CheckConstraint(f"document_type IN {DOCUMENT_TYPES!r}", name="valid_document_type"),
        CheckConstraint(
            f"verification_status IN {VERIFICATION_STATUSES!r}", name="valid_verification_status"
        ),
        CheckConstraint(f"upload_status IN {UPLOAD_STATUSES!r}", name="valid_upload_status"),
        CheckConstraint(f"scan_status IN {SCAN_STATUSES!r}", name="valid_scan_status"),
        CheckConstraint(
            "expiry_date IS NULL OR issue_date IS NULL OR expiry_date >= issue_date",
            name="valid_expiry_after_issue",
        ),
        Index("ix_staff_documents_staff_user_id", "staff_user_id"),
    )

    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upload_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    scan_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaces_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_documents.id"), nullable=True
    )
    reminder_eligible: Mapped[bool] = mapped_column(nullable=False, default=True)
