import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

CALL_DIRECTIONS = ("inbound", "outbound")
CALL_OUTCOMES = ("connected", "no_answer", "voicemail", "busy", "wrong_number", "other")


class ManualCallLog(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """This phase's own instruction section 18 — a call *log*, not a voice
    agent or telephony integration: no recording, no PBX/SIP connection,
    just the structured record a staff member enters after hanging up."""

    __tablename__ = "manual_call_logs"
    __table_args__ = (
        CheckConstraint(f"direction IN {CALL_DIRECTIONS!r}", name="valid_direction"),
        CheckConstraint(f"outcome IN {CALL_OUTCOMES!r}", name="valid_outcome"),
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="valid_call_window"),
        Index("ix_manual_call_logs_customer_id", "customer_id"),
        Index("ix_manual_call_logs_lead_id", "lead_id"),
        Index("ix_manual_call_logs_staff_user_id", "staff_user_id"),
    )

    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    staff_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    related_reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id"), nullable=True
    )
    related_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True
    )
