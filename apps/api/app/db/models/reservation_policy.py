from sqlalchemy import BigInteger, Boolean, CheckConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AuditedMixin, Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReservationPolicies(UUIDPrimaryKeyMixin, TimestampMixin, AuditedMixin, Base):
    """Global, single-row policy configuration — this phase's own
    instruction: "deposit required, advance booking limit, minimum/maximum
    notice, cancellation window, no-show window, grace period, buffer
    before/after, min/max party size." `singleton_guard` is a constant-valued
    unique column, the standard Postgres trick for enforcing at-most-one-row
    without inventing a fake foreign key nothing else can reference.

    `advance_booking_limit_days` doubles as "maximum notice" (how far ahead
    a booking may be made); `minimum_notice_minutes` is the separate lower
    bound the instruction also names (PROJECT_PLAN.md section 3.3's
    documented 60-minute approval cutoff is the seeded default — task
    #111). Two columns cover both bounds without a third, redundant
    "maximum notice" column duplicating the same meaning.

    `large_party_threshold` is PROJECT_PLAN.md section 11's rule that
    groups above this size are routed to events/bulk leads instead of the
    standard reservation flow, not merely rejected.
    """

    __tablename__ = "reservation_policies"
    __table_args__ = (
        CheckConstraint("singleton_guard", name="valid_singleton_guard"),
        CheckConstraint("advance_booking_limit_days > 0", name="valid_advance_booking_limit"),
        CheckConstraint("minimum_notice_minutes >= 0", name="valid_minimum_notice"),
        CheckConstraint("cancellation_window_minutes >= 0", name="valid_cancellation_window"),
        CheckConstraint("no_show_grace_minutes >= 0", name="valid_no_show_grace"),
        CheckConstraint("buffer_before_minutes >= 0", name="valid_buffer_before"),
        CheckConstraint("buffer_after_minutes >= 0", name="valid_buffer_after"),
        CheckConstraint("default_minimum_party_size > 0", name="valid_default_minimum_party_size"),
        CheckConstraint(
            "default_maximum_party_size >= default_minimum_party_size",
            name="valid_default_maximum_party_size",
        ),
        CheckConstraint(
            "large_party_threshold >= default_maximum_party_size",
            name="valid_large_party_threshold",
        ),
        CheckConstraint(
            "default_deposit_amount_minor IS NULL OR default_deposit_amount_minor >= 0",
            name="valid_default_deposit_amount_minor",
        ),
    )

    singleton_guard: Mapped[bool] = mapped_column(
        Boolean, unique=True, nullable=False, default=True
    )
    deposit_required_by_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    default_deposit_amount_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    advance_booking_limit_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    minimum_notice_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    cancellation_window_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    no_show_grace_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    buffer_before_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    buffer_after_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    default_minimum_party_size: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    default_maximum_party_size: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    large_party_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=18)
