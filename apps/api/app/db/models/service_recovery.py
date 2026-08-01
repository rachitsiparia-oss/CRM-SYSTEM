import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    AppendOnlyTimestampMixin,
    AuditedMixin,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

# GROWTH_AND_INTELLIGENCE.md section 12.6. Money-denominated types carry
# `value_minor`; `loyalty_credit` carries `points`; `apology_only`/
# `manager_follow_up`/`operational_correction` carry neither.
RECOVERY_TYPES = (
    "apology_only",
    "replacement",
    "refund_request",
    "approved_refund",
    "discount",
    "coupon",
    "loyalty_credit",
    "complimentary_item",
    "manager_follow_up",
    "operational_correction",
)
RECOVERY_STATUSES = (
    "proposed",
    "approval_required",
    "approved",
    "rejected",
    "executing",
    "completed",
    "failed",
    "reversed",
    "cancelled",
)
# Polymorphic — mirrors which existing, already-audited ledger/domain
# actually recorded the value. `execution_reference_id` has no FK (the
# referenced table depends on the type), the same tradeoff
# `TaskRecord.related_type`/`ConversationLink.linked_type` already make.
EXECUTION_REFERENCE_TYPES = (
    "loyalty_ledger_entry",
    "customer_credit_ledger_entry",
    "order_payment",
    "manual",
)


class CompensationApprovalRule(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """No value-threshold approval-routing precedent exists anywhere in the
    codebase (confirmed absent from `app.customer_credit`, whose
    `customer_credit.approve` permission is granted but never actually
    checked against a threshold) — this is Phase 13's own new pattern, not
    a reuse of an existing one. `recovery_type IS NULL` matches any type;
    `min_value_minor`/`max_value_minor` bound a range (both `NULL` matches
    any value, e.g. for `apology_only`). The most specific *active* rule
    matching a proposed action's type/value/complaint-severity governs;
    when no rule matches, the action requires no additional approval
    beyond the base `complaints.recovery.propose` permission."""

    __tablename__ = "compensation_approval_rules"
    __table_args__ = (
        CheckConstraint(
            f"recovery_type IS NULL OR recovery_type IN {RECOVERY_TYPES!r}",
            name="valid_recovery_type",
        ),
        CheckConstraint(
            "min_value_minor IS NULL OR min_value_minor >= 0", name="valid_min_value_minor"
        ),
        CheckConstraint(
            "max_value_minor IS NULL OR max_value_minor >= 0", name="valid_max_value_minor"
        ),
        CheckConstraint(
            "max_value_minor IS NULL OR min_value_minor IS NULL OR "
            "max_value_minor >= min_value_minor",
            name="valid_value_range",
        ),
    )

    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    recovery_type: Mapped[str | None] = mapped_column(String(24), nullable=True)
    min_value_minor: Mapped[int | None] = mapped_column(nullable=True)
    max_value_minor: Mapped[int | None] = mapped_column(nullable=True)
    applicable_severities: Mapped[list[str] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    required_permission: Mapped[str] = mapped_column(String(100), nullable=False)
    allow_self_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ServiceRecoveryAction(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Never mutates a balance directly — `app.service_recovery.execution`
    calls `app.loyalty.ledger.post_entry(entry_type="service_recovery_credit")`
    or `app.customer_credit.accounts.issue(issue_reason="service_recovery")`
    or `app.orders.service.record_payment`/`update_payment_status`
    (`orders.payments.manage`), and records the resulting row's id/type in
    `execution_reference_type`/`execution_reference_id`. `idempotency_key`
    is derived from `complaint_id:action_id:recovery_type` and passed
    through to whichever ledger executes the action, so a retried
    execution attempt cannot double-post."""

    __tablename__ = "service_recovery_actions"
    __table_args__ = (
        CheckConstraint(f"recovery_type IN {RECOVERY_TYPES!r}", name="valid_recovery_type"),
        CheckConstraint(f"status IN {RECOVERY_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "execution_reference_type IS NULL OR execution_reference_type IN "
            + repr(EXECUTION_REFERENCE_TYPES),
            name="valid_execution_reference_type",
        ),
        CheckConstraint("value_minor IS NULL OR value_minor >= 0", name="valid_value_minor"),
        CheckConstraint("points IS NULL OR points >= 0", name="valid_points"),
        Index("ix_service_recovery_actions_complaint_id", "complaint_id"),
        Index("ix_service_recovery_actions_customer_id", "customer_id"),
        Index("ix_service_recovery_actions_status", "status"),
        Index(
            "uq_service_recovery_actions_idempotency_key",
            "idempotency_key",
            unique=True,
        ),
    )

    complaint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("complaints.id"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), nullable=False)
    recovery_type: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    value_minor: Mapped[int | None] = mapped_column(nullable=True)
    points: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_by_staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff_users.id"), nullable=False
    )
    proposed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("compensation_approval_rules.id"), nullable=True
    )
    approved_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_reference_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    execution_reference_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    failed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_by_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    reversal_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)


class ServiceRecoveryActionHistory(UUIDPrimaryKeyMixin, AppendOnlyTimestampMixin, Base):
    __tablename__ = "service_recovery_action_history"
    __table_args__ = (
        Index("ix_service_recovery_action_history_action_id", "action_id"),
    )

    action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("service_recovery_actions.id"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("staff_users.id"), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
