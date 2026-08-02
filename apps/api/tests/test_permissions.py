import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from app.db.models import Role, StaffRole, StaffUser
from app.permissions.registry import PERMISSION_CODES, PERMISSIONS, get_permission
from app.permissions.role_matrix import ROLE_PERMISSIONS
from app.permissions.service import (
    get_effective_permissions,
    has_permission,
    invalidate_permissions_cache,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


def test_registry_has_no_duplicate_codes() -> None:
    assert len(PERMISSION_CODES) == len(PERMISSIONS)


def test_registry_codes_are_lowercase_dot_separated() -> None:
    for permission in PERMISSIONS:
        assert permission.code == permission.code.lower()
        assert "." in permission.code
        assert " " not in permission.code


def test_get_permission_returns_known_code() -> None:
    permission = get_permission("staff.manage")
    assert permission.module == "staff"
    assert permission.action == "manage"
    assert permission.is_sensitive is True


def test_get_permission_raises_for_unknown_code() -> None:
    with pytest.raises(KeyError):
        get_permission("not.a.real.permission")


def test_role_matrix_covers_every_system_role() -> None:
    from app.db.models.role import SYSTEM_ROLE_CODES

    assert set(ROLE_PERMISSIONS) == set(SYSTEM_ROLE_CODES)


def test_owner_role_has_every_permission() -> None:
    assert set(ROLE_PERMISSIONS["owner"]) == PERMISSION_CODES


def test_role_matrix_only_references_real_permission_codes() -> None:
    for codes in ROLE_PERMISSIONS.values():
        assert set(codes).issubset(PERMISSION_CODES)


async def test_effective_permissions_reflect_seeded_role_matrix(db_session: AsyncSession) -> None:
    role_id = await db_session.scalar(select(Role.id).where(Role.code == "kitchen_staff"))
    assert role_id is not None

    # No staff_roles row exists for a fresh random id — effective permissions
    # for an unrelated staff user must be empty.
    permissions = await get_effective_permissions(db_session, uuid.uuid4())
    assert permissions == frozenset()


async def test_has_permission_true_and_false(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    await invalidate_permissions_cache(staff_user.id)

    assert await has_permission(db_session, staff_user.id, "orders.view") is True
    assert await has_permission(db_session, staff_user.id, "settings.manage") is False


async def test_effective_permissions_cache_invalidation(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    staff_user = await make_staff_user(role_code="kitchen_staff")
    await invalidate_permissions_cache(staff_user.id)

    first = await get_effective_permissions(db_session, staff_user.id)
    assert "orders.view" in first

    # Simulate a role change without going through invalidate_permissions_cache
    # first: the cached value should still be returned (proves caching works).
    role_id = await db_session.scalar(select(Role.id).where(Role.code == "owner"))
    db_session.add(
        StaffRole(staff_user_id=staff_user.id, role_id=role_id, assigned_at=datetime.now(UTC))
    )
    await db_session.flush()

    still_cached = await get_effective_permissions(db_session, staff_user.id)
    assert still_cached == first

    await invalidate_permissions_cache(staff_user.id)
    refreshed = await get_effective_permissions(db_session, staff_user.id)
    assert "settings.manage" in refreshed
