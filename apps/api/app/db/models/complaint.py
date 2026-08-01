import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    AppendOnlyTimestampMixin,
    AuditedMixin,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

# GROWTH_AND_INTELLIGENCE.md section 12.2-12.3.
COMPLAINT_SOURCE_TYPES = (
    "feedback",
    "direct",
    "conversation",
    "staff_entry",
    "order",
    "reservation",
    "other",
)
COMPLAINT_CATEGORIES = (
    "food_quality",
    "incorrect_item",
    "missing_item",
    "packaging",
    "delay",
    "delivery",
    "payment",
    "refund",
    "reservation",
    "staff_behavior",
    "cleanliness",
    "allergy_or_dietary",
    "promotion",
    "loyalty",
    "communication",
    "corporate_order",
    "other",
)
COMPLAINT_SEVERITIES = ("low", "medium", "high", "critical")
COMPLAINT_PRIORITIES = ("low", "normal", "high", "urgent")
# The authoritative section-12.3 lifecycle, plus `cancelled` (a duplicate or
# invalid report needs a terminal non-`closed` state that doesn't imply a
# real resolution occurred — the same distinction `OfferStatus` draws
# between `cancelled` and `archived`). Recovery-approval states are
# deliberately NOT complaint statuses — they live on the linked
# `ServiceRecoveryAction.status` instead, keeping "is this complaint open"
# and "is this specific recovery action approved" independently queryable
# rather than overloading one enum with the other's states.
COMPLAINT_STATUSES = (
    "new",
    "acknowledged",
    "investigating",
    "awaiting_customer",
    "awaiting_internal",
    "resolution_proposed",
    "resolved",
    "closed",
    "reopened",
    "cancelled",
)
ROOT_CAUSE_CATEGORIES = (
    "process_failure",
    "preparation_error",
    "inventory_unavailable",
    "packaging_error",
    "delivery_delay",
    "staff_training_gap",
    "communication_failure",
    "system_failure",
    "supplier_issue",
    "policy_gap",
    "customer_expectation_mismatch",
    "unknown",
)
COMPLAINT_LINK_RELATIONSHIP_TYPES = ("duplicate_of", "related_to")
SLA_EVENT_TYPES = (
    "approaching_first_response",
    "breached_first_response",
    "approaching_acknowledgement",
    "breached_acknowledgement",
    "approaching_resolution",
    "breached_resolution",
    "approaching_follow_up",
    "breached_follow_up",
)
FOLLOW_UP_OUTCOMES = ("satisfied", "unsatisfied", "no_response", "escalated_again")


class Complaint(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """GROWTH_AND_INTELLIGENCE.md section 12.3-12.5; CORE_CRM_MODULES.md
    section 10.6/OPERATIONS_MODULES.md section 8.4's "complaint recovery"
    cross-module workflow.

    `is_hr_sensitive` is set once at creation (`category == "staff_behavior"`
    implies it, and it may also be set explicitly) and gates
    `complaints.hr_sensitive.read` at the service layer — no document
    defines this interaction precisely (flagged as an open design question
    during Phase 13 research), so it is handled the same way Staff
    Operations already handles `staff.hr_sensitive.read`: a narrower read
    permission required in addition to the base `complaints.view`, not a
    replacement for it.
    """

    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(f"source_type IN {COMPLAINT_SOURCE_TYPES!r}", name="valid_source_type"),
        CheckConstraint(f"category IN {COMPLAINT_CATEGORIES!r}", name="valid_category"),
        CheckConstraint(f"severity IN {COMPLAINT_SEVERITIES!r}", name="valid_severity"),
        CheckConstraint(f"priority IN {COMPLAINT_PRIORITIES!r}", name="valid_priority"),
        CheckConstraint(f"status IN {COMPLAINT_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "root_cause IS NULL OR root_cause IN " + repr(ROOT_CAUSE_CATEGORIES),
            name="valid_root_cause",
        ),
        CheckConstraint(
            "customer_sentiment IS NULL OR customer_sentiment IN "
            "('positive', 'neutral', 'negative', 'mixed')",
            name="valid_customer_sentiment",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR acknowledged_at IS NULL OR resolved_at >= acknowledged_at",
            name="valid_resolution_ordering",
        ),
        CheckConstraint(
            "closed_at IS NULL OR resolved_at IS NULL OR closed_at >= resolved_at",
            name="valid_closure_ordering",
        ),
        Index("ix_complaints_customer_id", "customer_id"),
        Index("ix_complaints_status", "status"),
        Index("ix_complaints_severity", "severity"),
        Index("ix_complaints_priority", "priority"),
        Index("ix_complaints_category", "category"),
        Index("ix_complaints_assigned_staff_id", "assigned_staff_id"),
        Index("ix_complaints_assigned_department_id", "assigned_department_id"),
        Index("ix_complaints_created_at", "created_at"),
        Index("ix_complaints_resolution_due_at", "resolution_due_at"),
        Index("ix_complaints_follow_up_due_at", "follow_up_due_at"),
        Index("ix_complaints_order_id", "order_id"),
        Index("ix_complaints_reservation_id", "reservation_id"),
        Index("ix_complaints_conversation_id", "conversation_id"),
        Index("ix_complaints_feedback_id", "feedback_id"),
    )

    complaint_number: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    feedback_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("feedback_entries.id"), nullable=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id"), nullable=True)
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reservations.id"), nullable=True
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    current_escalation_level: Mapped[int] = mapped_column(nullable=False, default=0)
    sla_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sla_policies.id"), nullable=True
    )
    first_response_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledgement_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    follow_up_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reopened_count: Mapped[int] = mapped_column(nullable=False, default=0)
    customer_sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_visible_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_hr_sensitive: Mapped[bool] = mapped_column(nullable=False, default=False)


class ComplaintStatusHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    __tablename__ = "complaint_status_history"
    __table_args__ = (Index("ix_complaint_status_history_complaint_id", "complaint_id"),)

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ComplaintRootCauseHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Root cause "may be updated as investigation progresses, with history
    retained" (section 12.7) — independently revisable from `status`, so a
    separate history table rather than folding into
    `ComplaintStatusHistory`."""

    __tablename__ = "complaint_root_cause_history"
    __table_args__ = (Index("ix_complaint_root_cause_history_complaint_id", "complaint_id"),)

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    from_root_cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_root_cause: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ComplaintAssignment(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """History of assignment changes; the *current* assignment is mirrored
    onto `Complaint.assigned_staff_id`/`.assigned_department_id` for query
    performance, the same denormalization `TaskRecord` uses for its own
    single current assignee."""

    __tablename__ = "complaint_assignments"
    __table_args__ = (
        CheckConstraint(
            "assigned_staff_id IS NOT NULL OR assigned_department_id IS NOT NULL",
            name="requires_staff_or_department",
        ),
        Index("ix_complaint_assignments_complaint_id", "complaint_id"),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    assigned_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ComplaintNote(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Internal-only by design — `Complaint.customer_visible_summary` is
    the sole customer-facing surface, so notes never need a visibility
    toggle that could be flipped incorrectly (CLAUDE.md section 6.2's "no
    broad exposure of internal notes")."""

    __tablename__ = "complaint_notes"
    __table_args__ = (Index("ix_complaint_notes_complaint_id", "complaint_id"),)

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    author_staff_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("staff_users.id"), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)


class ComplaintEscalation(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """`dedup_key` (`complaint:{id}:level:{level}`) prevents the same
    complaint from being escalated to the same level twice — the
    deduplication requirement instruction section 5.4 and
    INTEGRATIONS_AUTOMATIONS_REALTIME.md section 17.4 both require."""

    __tablename__ = "complaint_escalations"
    __table_args__ = (
        Index("ix_complaint_escalations_complaint_id", "complaint_id"),
        Index("uq_complaint_escalations_dedup_key", "dedup_key", unique=True),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    level: Mapped[int] = mapped_column(nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    previous_assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    previous_assigned_department_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    new_assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    new_assigned_department_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("departments.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    dedup_key: Mapped[str] = mapped_column(String(160), nullable=False)


class ComplaintSlaEvent(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Written by `app.complaints.sla.check_sla_events` — a deterministic,
    idempotent function callable repeatedly without duplicating rows
    (`dedup_key` unique), matching the "engine, not scheduler" split; live
    recurring invocation belongs to Phase 15."""

    __tablename__ = "complaint_sla_events"
    __table_args__ = (
        CheckConstraint(f"event_type IN {SLA_EVENT_TYPES!r}", name="valid_event_type"),
        Index("ix_complaint_sla_events_complaint_id", "complaint_id"),
        Index("uq_complaint_sla_events_dedup_key", "dedup_key", unique=True),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    notified: Mapped[bool] = mapped_column(nullable=False, default=False)
    dedup_key: Mapped[str] = mapped_column(String(160), nullable=False)


class ComplaintFollowUp(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    __tablename__ = "complaint_follow_ups"
    __table_args__ = (
        CheckConstraint(
            f"outcome IS NULL OR outcome IN {FOLLOW_UP_OUTCOMES!r}", name="valid_outcome"
        ),
        Index("ix_complaint_follow_ups_complaint_id", "complaint_id"),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(24), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )


class ComplaintLink(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    """Duplicate/related complaint linkage — instruction section 12
    ("duplicate/related complaint linkage"). Distinct from the direct
    `order_id`/`reservation_id`/`conversation_id`/`feedback_id` columns on
    `Complaint` itself, which cover the single originating-record link;
    this covers complaint-to-complaint relationships only."""

    __tablename__ = "complaint_links"
    __table_args__ = (
        CheckConstraint(
            f"relationship_type IN {COMPLAINT_LINK_RELATIONSHIP_TYPES!r}",
            name="valid_relationship_type",
        ),
        CheckConstraint("complaint_id != related_complaint_id", name="no_self_link"),
        Index(
            "uq_complaint_links_pair",
            "complaint_id",
            "related_complaint_id",
            unique=True,
        ),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    related_complaint_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("complaints.id"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
