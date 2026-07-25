import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models import Department, Role, RolePermission, StaffInvitation, StaffUser
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _staff_user_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "auth_user_id": uuid.uuid4(),
        "employee_code": f"TEST-{suffix}",
        "first_name": "Test",
        "last_name": "User",
        "display_name": "Test User",
        "email": f"test-{suffix}@example.test",
        "account_status": "active",
        "employment_status": "full_time",
    }
    base.update(overrides)
    return base


async def test_staff_user_rejects_invalid_account_status(db_session: AsyncSession) -> None:
    staff_user = StaffUser(**_staff_user_kwargs(account_status="not_a_real_status"))
    db_session.add(staff_user)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_staff_user_rejects_invalid_employment_status(db_session: AsyncSession) -> None:
    staff_user = StaffUser(**_staff_user_kwargs(employment_status="not_a_real_status"))
    db_session.add(staff_user)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_staff_user_accepts_archived_status(db_session: AsyncSession) -> None:
    """Regression test for the Phase 3 doc-reconciliation fix — `archived`
    was missing from DATABASE_AND_API.md section 4.1 even though
    SECURITY_PERFORMANCE_AND_QUALITY.md section 3.6 already listed it."""
    staff_user = StaffUser(**_staff_user_kwargs(account_status="archived"))
    db_session.add(staff_user)
    await db_session.flush()
    assert staff_user.account_status == "archived"


async def test_staff_user_email_unique_only_among_active_rows(db_session: AsyncSession) -> None:
    email = f"dup-{uuid.uuid4().hex[:10]}@example.test"

    first = StaffUser(**_staff_user_kwargs(email=email))
    db_session.add(first)
    await db_session.flush()
    first.deleted_at = datetime.now(UTC)
    await db_session.flush()

    # A second, non-deleted row with the same email must be allowed once the
    # first is soft-deleted — "unique active normalized email".
    second = StaffUser(**_staff_user_kwargs(email=email))
    db_session.add(second)
    await db_session.flush()
    assert second.id != first.id


async def test_staff_user_email_conflicts_while_both_active(db_session: AsyncSession) -> None:
    email = f"dup-{uuid.uuid4().hex[:10]}@example.test"
    db_session.add(StaffUser(**_staff_user_kwargs(email=email)))
    await db_session.flush()

    db_session.add(StaffUser(**_staff_user_kwargs(email=email)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_role_permission_rejects_invalid_scope_type(db_session: AsyncSession) -> None:
    role_id = await db_session.scalar(select(Role.id).where(Role.code == "owner"))
    from app.db.models import Permission

    permission_id = await db_session.scalar(
        select(Permission.id).where(Permission.code == "dashboard.view")
    )
    db_session.add(
        RolePermission(role_id=role_id, permission_id=permission_id, scope_type="bogus_scope")
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_staff_invitation_rejects_invalid_status(db_session: AsyncSession) -> None:
    owner = StaffUser(**_staff_user_kwargs())
    db_session.add(owner)
    await db_session.flush()

    role_id = await db_session.scalar(select(Role.id).where(Role.code == "kitchen_staff"))
    department_id = await db_session.scalar(select(Department.id).limit(1))

    invitation = StaffInvitation(
        id=uuid.uuid4(),
        email="invitee@example.test",
        first_name="Invitee",
        department_id=department_id,
        intended_role_id=role_id,
        invited_by=owner.id,
        status="not_a_real_status",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(invitation)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_staff_invitation_defaults_to_pending(db_session: AsyncSession) -> None:
    owner = StaffUser(**_staff_user_kwargs())
    db_session.add(owner)
    await db_session.flush()

    role_id = await db_session.scalar(select(Role.id).where(Role.code == "kitchen_staff"))
    invitation = StaffInvitation(
        id=uuid.uuid4(),
        email=f"invitee-{uuid.uuid4().hex[:8]}@example.test",
        first_name="Invitee",
        intended_role_id=role_id,
        invited_by=owner.id,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(invitation)
    await db_session.flush()
    assert invitation.status == "pending"
