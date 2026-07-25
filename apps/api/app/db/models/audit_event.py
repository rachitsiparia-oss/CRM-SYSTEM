import uuid
from typing import Any

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppendOnlyTimestampMixin, Base, UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Append-only audit trail for sensitive and consequential actions —
    DATABASE_AND_API.md section 16.5, CLAUDE.md section 6.6.

    Rows are never edited or deleted through the application; only ever
    inserted. No secrets or unnecessary sensitive payloads belong in
    `safe_metadata`, `before_summary`, or `after_summary`.
    """

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_actor_created", "actor_id", "created_at"),
        Index("ix_audit_events_target", "target_type", "target_id"),
    )

    actor_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    action_code: Mapped[str] = mapped_column(String(120), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    safe_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    before_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    after_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
