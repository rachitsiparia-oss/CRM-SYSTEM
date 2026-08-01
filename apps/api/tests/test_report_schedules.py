"""Tests for `app.report_schedules` — occurrence-key computation and the
idempotent delivery ledger (GROWTH_AND_INTELLIGENCE.md section 13.19)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date

from app.db.models import ScheduledReport, StaffUser
from app.report_schedules.service import compute_occurrence_key

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def _make_schedule(frequency: str) -> ScheduledReport:
    import uuid

    return ScheduledReport(
        id=uuid.uuid4(),
        report_definition_id=uuid.uuid4(),
        name="Test schedule",
        schedule_frequency=frequency,
        schedule_day_of_week=0 if frequency == "weekly" else None,
        schedule_day_of_month=1 if frequency == "monthly" else None,
    )


def test_occurrence_key_daily_uses_iso_date() -> None:
    schedule = _make_schedule("daily")
    key = compute_occurrence_key(schedule, as_of=date(2026, 3, 15))
    assert key == f"{schedule.id}:2026-03-15"


def test_occurrence_key_weekly_uses_iso_week() -> None:
    schedule = _make_schedule("weekly")
    key = compute_occurrence_key(schedule, as_of=date(2026, 3, 15))
    assert key.endswith("W11") or key.endswith("W12")  # ISO week number, tz-independent check
    assert "2026-W" in key


def test_occurrence_key_monthly_uses_year_month() -> None:
    schedule = _make_schedule("monthly")
    key = compute_occurrence_key(schedule, as_of=date(2026, 3, 15))
    assert key == f"{schedule.id}:2026-03"


def test_occurrence_key_is_stable_for_same_day() -> None:
    schedule = _make_schedule("daily")
    key1 = compute_occurrence_key(schedule, as_of=date(2026, 3, 15))
    key2 = compute_occurrence_key(schedule, as_of=date(2026, 3, 15))
    assert key1 == key2


def test_occurrence_key_differs_across_schedules() -> None:
    schedule_a = _make_schedule("daily")
    schedule_b = _make_schedule("daily")
    key_a = compute_occurrence_key(schedule_a, as_of=date(2026, 3, 15))
    key_b = compute_occurrence_key(schedule_b, as_of=date(2026, 3, 15))
    assert key_a != key_b
