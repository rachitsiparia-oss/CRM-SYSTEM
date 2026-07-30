import uuid

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

UPLOAD_STATUSES = ("pending", "uploaded", "failed")
SCAN_STATUSES = ("pending", "clean", "infected", "skipped")


class MessageAttachment(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, SoftDeleteMixin, Base):
    """DATABASE_AND_API.md section 12.3, using the same private-storage-
    path/signed-URL discipline `app.storage` established for product
    images (TOOLS.md section 5.3). Soft-deletable — this phase's own
    instruction's privacy/retention section explicitly allows controlled
    attachment deletion, unlike the immutable message it belongs to."""

    __tablename__ = "message_attachments"
    __table_args__ = (
        CheckConstraint(f"upload_status IN {UPLOAD_STATUSES!r}", name="valid_upload_status"),
        CheckConstraint(f"scan_status IN {SCAN_STATUSES!r}", name="valid_scan_status"),
        CheckConstraint("size_bytes > 0", name="valid_size_bytes"),
        Index("ix_message_attachments_message_id", "message_id"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(80), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    external_provider_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    upload_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    scan_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
