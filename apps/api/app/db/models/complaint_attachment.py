import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


class ComplaintAttachment(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Mirrors `KnowledgeAttachment`/`FeedbackAttachment`'s private-storage-
    path/signed-URL discipline (`app.storage`, TOOLS.md section 5.3)."""

    __tablename__ = "complaint_attachments"
    __table_args__ = (
        CheckConstraint(
            "upload_status IN ('pending', 'uploaded', 'failed')", name="valid_upload_status"
        ),
        CheckConstraint(
            "scan_status IN ('pending', 'clean', 'infected', 'skipped')",
            name="valid_scan_status",
        ),
        CheckConstraint("size_bytes > 0", name="valid_size_bytes"),
        Index("ix_complaint_attachments_complaint_id", "complaint_id"),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upload_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    scan_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
