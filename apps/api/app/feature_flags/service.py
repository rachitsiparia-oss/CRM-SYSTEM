"""Feature flag CRUD and a cache-backed evaluation helper.

CLAUDE.md section 2 forbids a generic customization/targeting engine — this
is deliberately just a stable on/off switch per `code`, no percentage
rollout, no per-role targeting. `is_enabled()` is the hot-path call sites
elsewhere in the codebase should use; it reads through `app.cache` (short
TTL, safe-degrade-to-a-fresh-DB-read on any cache failure) rather than
hitting Postgres on every check.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import build_key
from app.cache.service import delete as cache_delete
from app.cache.service import get_json as cache_get_json
from app.cache.service import set_json as cache_set_json
from app.db.models import FeatureFlag, StaffUser
from app.feature_flags.errors import DuplicateFeatureFlagCodeError, FeatureFlagNotFoundError


def _cache_key(code: str) -> str:
    return build_key("settings", "feature_flag", code)


async def list_flags(session: AsyncSession) -> list[FeatureFlag]:
    rows = await session.scalars(select(FeatureFlag).order_by(FeatureFlag.code))
    return list(rows.all())


async def get_flag(session: AsyncSession, flag_id: uuid.UUID) -> FeatureFlag:
    flag = await session.get(FeatureFlag, flag_id)
    if flag is None:
        raise FeatureFlagNotFoundError(f"Feature flag {flag_id} not found.")
    return flag


async def create_flag(
    session: AsyncSession,
    *,
    actor: StaffUser,
    code: str,
    name: str,
    description: str | None,
    is_enabled: bool = False,
) -> FeatureFlag:
    existing = await session.scalar(select(FeatureFlag).where(FeatureFlag.code == code))
    if existing is not None:
        raise DuplicateFeatureFlagCodeError(f"Feature flag code {code!r} already exists.")
    flag = FeatureFlag(
        code=code,
        name=name,
        description=description,
        is_enabled=is_enabled,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(flag)
    await session.flush()
    return flag


async def set_flag_enabled(
    session: AsyncSession, *, flag: FeatureFlag, actor: StaffUser, is_enabled: bool
) -> FeatureFlag:
    flag.is_enabled = is_enabled
    flag.updated_by = actor.id
    await session.flush()
    await cache_delete(_cache_key(flag.code))
    return flag


async def is_enabled(session: AsyncSession, code: str, *, default: bool = False) -> bool:
    cached = await cache_get_json(_cache_key(code))
    if cached is not None:
        result: bool = cached["is_enabled"]
        return result

    flag = await session.scalar(select(FeatureFlag).where(FeatureFlag.code == code))
    if flag is None:
        # A caller-supplied fallback is never cached: it isn't a database
        # fact, differs freely by call site, and caching it would leave a
        # stale wrong answer for up to a full TTL if the flag is created
        # moments later (nothing invalidates a "not found" cache entry).
        return default
    await cache_set_json(_cache_key(code), {"is_enabled": flag.is_enabled}, family="settings")
    return flag.is_enabled
