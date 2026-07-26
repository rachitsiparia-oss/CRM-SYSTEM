import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin

# CORE_CRM_MODULES.md section 5.9.
LEAD_ACTIVITY_TYPES = (
    "call",
    "email",
    "whatsapp",
    "meeting",
    "proposal",
    "note",
    "status_change",
    "assignment",
    "follow_up_created",
    "follow_up_completed",
    "file_added",
    "customer_conversion",
    "order_conversion",
)

# Activity types that count as "contact" for Lead.last_contact_at and the
# "leads with no contact" filter — a Phase 5 implementation decision, since
# neither canonical document defines this subset explicitly.
CONTACT_ACTIVITY_TYPES = ("call", "email", "whatsapp", "meeting")


class LeadActivity(UUIDPrimaryKeyMixin, Base):
    """DATABASE_AND_API.md section 7.2. This is the lead's own structured
    sales-activity timeline (call/email/meeting/proposal/etc) — distinct
    from `audit_events`, which still separately records
    security/business-critical facts about the lead (created, assigned,
    status changed) per CLAUDE.md section 19. Both are written for the
    activities that matter for both purposes; this table is never a
    substitute for the audit trail."""

    __tablename__ = "lead_activities"
    __table_args__ = (
        CheckConstraint(f"activity_type IN {LEAD_ACTIVITY_TYPES!r}", name="valid_activity_type"),
        Index("ix_lead_activities_lead_id", "lead_id"),
    )

    lead_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("leads.id"), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    activity_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
