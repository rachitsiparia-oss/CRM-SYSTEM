"""Effective-permission calculation and caching.

A staff user's effective permissions are the union of every permission
granted to every active role assigned to them
(`staff_roles` -> `role_permissions` -> `permissions`,
DATABASE_AND_API.md section 4.5). Recomputing this on every request would
mean two extra joined queries per protected endpoint; this module caches
the result in-process with a short TTL, invalidated explicitly whenever a
role assignment changes.

In-process only, correct for the single API instance this project
currently runs — a multi-instance deployment would need a shared cache
(Redis), deferred to the Phase 16/17 infrastructure hardening, matching
`app.core.rate_limit`.
"""

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Permission, Role, RolePermission, StaffRole

_CACHE_TTL_SECONDS = 300


@dataclass
class _CacheEntry:
    permissions: frozenset[str]
    cached_at: float = field(default_factory=time.monotonic)


class _EffectivePermissionCache:
    def __init__(self) -> None:
        self._entries: dict[uuid.UUID, _CacheEntry] = {}
        self._lock = Lock()

    def get(self, staff_user_id: uuid.UUID) -> frozenset[str] | None:
        with self._lock:
            entry = self._entries.get(staff_user_id)
            if entry is None:
                return None
            if time.monotonic() - entry.cached_at > _CACHE_TTL_SECONDS:
                del self._entries[staff_user_id]
                return None
            return entry.permissions

    def set(self, staff_user_id: uuid.UUID, permissions: frozenset[str]) -> None:
        with self._lock:
            self._entries[staff_user_id] = _CacheEntry(permissions=permissions)

    def invalidate(self, staff_user_id: uuid.UUID) -> None:
        with self._lock:
            self._entries.pop(staff_user_id, None)


_cache = _EffectivePermissionCache()


def invalidate_permissions_cache(staff_user_id: uuid.UUID) -> None:
    _cache.invalidate(staff_user_id)


async def get_effective_permissions(
    session: AsyncSession, staff_user_id: uuid.UUID
) -> frozenset[str]:
    cached = _cache.get(staff_user_id)
    if cached is not None:
        return cached

    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(StaffRole, StaffRole.role_id == Role.id)
        .where(
            StaffRole.staff_user_id == staff_user_id,
            Role.is_active.is_(True),
            RolePermission.scope_type != "none",
        )
        .distinct()
    )
    result = await session.scalars(stmt)
    permissions = frozenset(result.all())
    _cache.set(staff_user_id, permissions)
    return permissions


async def has_permission(
    session: AsyncSession, staff_user_id: uuid.UUID, permission_code: str
) -> bool:
    permissions = await get_effective_permissions(session, staff_user_id)
    return permission_code in permissions
