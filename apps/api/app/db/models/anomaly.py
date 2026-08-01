import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin

# GROWTH_AND_INTELLIGENCE.md section 15.7 / Phase 14 instruction section 12.
ANOMALY_RULE_TYPES = (
    "absolute_threshold",
    "pct_change_prior_period",
    "rolling_average_deviation",
    "count_rate_threshold",
    "consecutive_deterioration",
    "missing_activity",
)
ANOMALY_COMPARISON_OPERATORS = ("gt", "gte", "lt", "lte")
ANOMALY_SEVERITIES = ("low", "medium", "high", "critical")
ANOMALY_FINDING_STATUSES = ("open", "acknowledged", "investigating", "resolved", "dismissed")


class AnomalyRule(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """A deterministic anomaly-detection rule over one `app.analytics_core`
    metric. `metric_code` is validated against the in-code metric registry
    at the service layer, not a DB FK, since the registry is code (not a
    table) by design (GROWTH_AND_INTELLIGENCE.md section 13.4: "metric
    definitions must not live only in frontend code" — the backend
    registry is the single source, and rules reference it by string code).

    `threshold_value` is a generic statistical rule parameter (e.g. "20"
    for a 20% deviation threshold), not a monetary business value, so it
    intentionally does not use the `_minor` BIGINT convention.
    """

    __tablename__ = "anomaly_rules"
    __table_args__ = (
        CheckConstraint(f"rule_type IN {ANOMALY_RULE_TYPES!r}", name="valid_rule_type"),
        CheckConstraint(
            "comparison_operator IS NULL OR comparison_operator IN "
            f"{ANOMALY_COMPARISON_OPERATORS!r}",
            name="valid_comparison_operator",
        ),
        CheckConstraint(f"severity IN {ANOMALY_SEVERITIES!r}", name="valid_severity"),
        CheckConstraint("minimum_sample_size >= 1", name="valid_minimum_sample_size"),
        CheckConstraint("cooldown_hours >= 0", name="non_negative_cooldown_hours"),
        Index("uq_anomaly_rules_code", "code", unique=True),
        Index("ix_anomaly_rules_metric_code", "metric_code"),
        Index("ix_anomaly_rules_is_active", "is_active"),
    )

    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric_code: Mapped[str] = mapped_column(String(80), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    comparison_operator: Mapped[str | None] = mapped_column(String(4), nullable=True)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    rolling_window_periods: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimum_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cooldown_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    notify_task: Mapped[bool] = mapped_column(nullable=False, default=False)
    notify_role_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AnomalyFinding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single detected anomaly instance, with a full lifecycle
    (GROWTH_AND_INTELLIGENCE.md section 15.7: "acknowledgement state").
    `dedup_key` (`f"{rule_id}:{observed_window_start.date()}"`) enforces
    the rule's dedup/cooldown requirement the same way
    `ComplaintEscalation.dedup_key` does for escalations."""

    __tablename__ = "anomaly_findings"
    __table_args__ = (
        CheckConstraint(f"severity IN {ANOMALY_SEVERITIES!r}", name="valid_severity"),
        CheckConstraint(f"status IN {ANOMALY_FINDING_STATUSES!r}", name="valid_status"),
        CheckConstraint(
            "observed_window_end >= observed_window_start", name="valid_observed_window_range"
        ),
        Index("uq_anomaly_findings_dedup_key", "dedup_key", unique=True),
        Index("ix_anomaly_findings_anomaly_rule_id", "anomaly_rule_id"),
        Index("ix_anomaly_findings_status", "status"),
        Index("ix_anomaly_findings_metric_code", "metric_code"),
    )

    anomaly_rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("anomaly_rules.id"), nullable=False
    )
    metric_code: Mapped[str] = mapped_column(String(80), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(160), nullable=False)
    baseline_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    baseline_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observed_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    expected_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    deviation_pct: Mapped[Decimal | None] = mapped_column(Numeric(9, 4), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    evidence: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("staff_users.id"), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    linked_task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_records.id"), nullable=True
    )
