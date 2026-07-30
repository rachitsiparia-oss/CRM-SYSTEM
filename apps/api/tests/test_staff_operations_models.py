import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from app.db.models import (
    AttendanceRecord,
    LeaveRequest,
    LeaveType,
    PerformanceReview,
    StaffAvailabilityWindow,
    StaffCertification,
    StaffEmploymentProfile,
    StaffShift,
    StaffUser,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


async def _make_staff_user(session: AsyncSession, **overrides: object) -> StaffUser:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "auth_user_id": uuid.uuid4(),
        "employee_code": f"TEST-{suffix}",
        "first_name": "Test",
        "display_name": "Test User",
        "email": f"test-{suffix}@example.test",
        "account_status": "active",
        "employment_status": "full_time",
    }
    base.update(overrides)
    staff_user = StaffUser(**base)
    session.add(staff_user)
    await session.flush()
    return staff_user


async def test_shift_rejects_end_before_start(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    now = datetime.now(UTC)
    shift = StaffShift(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        shift_date=date.today(),
        start_at=now,
        end_at=now - timedelta(hours=1),
        status="scheduled",
    )
    db_session.add(shift)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_shift_allows_overnight_range(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    start = datetime(2026, 8, 1, 22, 0, tzinfo=UTC)
    end = datetime(2026, 8, 2, 6, 0, tzinfo=UTC)
    shift = StaffShift(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        shift_date=date(2026, 8, 1),
        start_at=start,
        end_at=end,
        status="scheduled",
    )
    db_session.add(shift)
    await db_session.flush()
    assert shift.end_at > shift.start_at


async def test_attendance_rejects_checkout_before_checkin(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    now = datetime.now(UTC)
    record = AttendanceRecord(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        attendance_date=date.today(),
        status="present",
        actual_check_in_at=now,
        actual_check_out_at=now - timedelta(hours=1),
    )
    db_session.add(record)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_attendance_rejects_duplicate_date(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    today = date.today()
    db_session.add(
        AttendanceRecord(
            id=uuid.uuid4(), staff_user_id=staff.id, attendance_date=today, status="present"
        )
    )
    await db_session.flush()
    db_session.add(
        AttendanceRecord(
            id=uuid.uuid4(), staff_user_id=staff.id, attendance_date=today, status="absent"
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_leave_request_rejects_end_before_start(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    leave_type = LeaveType(
        id=uuid.uuid4(), name=f"Type-{uuid.uuid4().hex[:6]}", code=uuid.uuid4().hex[:6]
    )
    db_session.add(leave_type)
    await db_session.flush()
    request = LeaveRequest(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        leave_type_id=leave_type.id,
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 5),
        status="draft",
    )
    db_session.add(request)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_certification_rejects_expiry_before_issue(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    certification = StaffCertification(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        certification_type="Food Handler",
        issue_date=date(2026, 1, 1),
        expiry_date=date(2025, 1, 1),
    )
    db_session.add(certification)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_performance_review_rejects_invalid_rating(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    reviewer = await _make_staff_user(db_session)
    review = PerformanceReview(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        reviewer_id=reviewer.id,
        cycle_label="2026 H1",
        period_start_date=date(2026, 1, 1),
        period_end_date=date(2026, 6, 30),
        overall_rating=7,
    )
    db_session.add(review)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_performance_review_rejects_period_end_before_start(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    reviewer = await _make_staff_user(db_session)
    review = PerformanceReview(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        reviewer_id=reviewer.id,
        cycle_label="2026 H1",
        period_start_date=date(2026, 6, 30),
        period_end_date=date(2026, 1, 1),
    )
    db_session.add(review)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_employment_profile_rejects_self_reporting(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    profile = StaffEmploymentProfile(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        reporting_manager_id=staff.id,
        joining_date=date(2026, 1, 1),
    )
    db_session.add(profile)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_availability_window_requires_day_or_date(db_session: AsyncSession) -> None:
    staff = await _make_staff_user(db_session)
    window = StaffAvailabilityWindow(
        id=uuid.uuid4(),
        staff_user_id=staff.id,
        availability_type="available",
        day_of_week=None,
        specific_date=None,
    )
    db_session.add(window)
    with pytest.raises(IntegrityError):
        await db_session.flush()
