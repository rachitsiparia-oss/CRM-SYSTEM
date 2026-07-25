"""Idempotent seed functions for departments, roles, the permission
registry, and the default role-permission matrix.

Called from `app.db.seed.run_seed()`. Safe to rerun: permissions are
upserted to always match `app.permissions.registry` exactly (the registry
is code-owned, never admin-edited); departments, roles, and role-permission
grants are inserted only if missing, so admin customizations made later
through the API are never overwritten by a reseed.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Department, Permission, Role, RolePermission, StaffUser
from app.db.models.role import SYSTEM_ROLE_CODES
from app.permissions.registry import PERMISSIONS
from app.permissions.role_matrix import ROLE_PERMISSIONS

DEPARTMENTS: tuple[tuple[str, str], ...] = (
    ("leadership", "Leadership"),
    ("operations", "Operations"),
    ("kitchen", "Kitchen"),
    ("inventory", "Inventory"),
    ("reservations", "Reservations"),
    ("customer_support", "Customer Support"),
    ("marketing", "Marketing"),
    ("finance", "Finance"),
    ("hr", "HR"),
    ("delivery", "Delivery"),
)

ROLE_NAMES: dict[str, str] = {
    "owner": "Owner",
    "general_manager": "General Manager",
    "operations_manager": "Operations Manager",
    "finance_manager": "Finance Manager",
    "kitchen_manager": "Kitchen Manager",
    "inventory_manager": "Inventory Manager",
    "reservation_manager": "Reservation Manager",
    "customer_support_agent": "Customer Support Agent",
    "marketing_manager": "Marketing Manager",
    "hr_manager": "HR Manager",
    "shift_supervisor": "Shift Supervisor",
    "kitchen_staff": "Kitchen Staff",
    "front_of_house_staff": "Front-of-House Staff",
    "delivery_coordinator": "Delivery Coordinator",
    "read_only_auditor": "Read-Only Auditor",
}


async def seed_departments(session: AsyncSession) -> None:
    for code, name in DEPARTMENTS:
        stmt = (
            pg_insert(Department)
            .values(id=uuid.uuid4(), code=code, name=name, is_active=True)
            .on_conflict_do_nothing(index_elements=["code"])
        )
        await session.execute(stmt)


async def seed_roles(session: AsyncSession) -> None:
    assert set(ROLE_NAMES) == set(SYSTEM_ROLE_CODES)
    assert set(ROLE_PERMISSIONS) == set(SYSTEM_ROLE_CODES)
    for code in SYSTEM_ROLE_CODES:
        stmt = (
            pg_insert(Role)
            .values(
                id=uuid.uuid4(),
                code=code,
                name=ROLE_NAMES[code],
                is_system_role=True,
                is_active=True,
            )
            .on_conflict_do_nothing(index_elements=["code"])
        )
        await session.execute(stmt)


async def seed_permissions(session: AsyncSession) -> None:
    for permission in PERMISSIONS:
        stmt = pg_insert(Permission).values(
            id=uuid.uuid4(),
            code=permission.code,
            module=permission.module,
            action=permission.action,
            description=permission.description,
            is_sensitive=permission.is_sensitive,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["code"],
            set_={
                "module": stmt.excluded.module,
                "action": stmt.excluded.action,
                "description": stmt.excluded.description,
                "is_sensitive": stmt.excluded.is_sensitive,
            },
        )
        await session.execute(stmt)


async def seed_role_permissions(session: AsyncSession) -> None:
    role_ids = {
        row.code: row.id for row in (await session.execute(select(Role.code, Role.id))).all()
    }
    permission_ids = {
        row.code: row.id
        for row in (await session.execute(select(Permission.code, Permission.id))).all()
    }

    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        role_id = role_ids[role_code]
        for permission_code in permission_codes:
            permission_id = permission_ids[permission_code]
            stmt = (
                pg_insert(RolePermission)
                .values(role_id=role_id, permission_id=permission_id, scope_type="all")
                .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
            )
            await session.execute(stmt)


async def bootstrap_owner(
    session: AsyncSession,
    *,
    auth_user_id: uuid.UUID,
    email: str,
    first_name: str,
    last_name: str,
    employee_code: str = "EMP-0001",
) -> StaffUser:
    """Link a real Supabase Auth user to the first `staff_users` row with
    the `owner` role, breaking the bootstrap chicken-and-egg problem: every
    other staff account is created through the invitation workflow, which
    requires an already-privileged inviter to exist.

    Idempotent: if a staff_user already exists for this auth_user_id, it is
    returned unchanged rather than duplicated.
    """
    existing = await session.scalar(select(StaffUser).where(StaffUser.auth_user_id == auth_user_id))
    if existing is not None:
        return existing

    owner_role_id = await session.scalar(select(Role.id).where(Role.code == "owner"))
    if owner_role_id is None:
        raise RuntimeError("Cannot bootstrap owner: roles have not been seeded yet.")

    staff_user = StaffUser(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
        employee_code=employee_code,
        first_name=first_name,
        last_name=last_name,
        display_name=f"{first_name} {last_name}".strip(),
        email=email,
        account_status="active",
        employment_status="full_time",
        is_privileged=True,
    )
    session.add(staff_user)
    await session.flush()

    from app.db.models import StaffRole

    session.add(
        StaffRole(
            staff_user_id=staff_user.id,
            role_id=owner_role_id,
            assigned_by=staff_user.id,
            assigned_at=datetime.now(UTC),
        )
    )
    return staff_user


def default_invitation_expiry() -> datetime:
    return datetime.now(UTC) + timedelta(days=7)
