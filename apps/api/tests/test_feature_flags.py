"""Tests for `app.feature_flags` — create/list/toggle and the
cache-backed `is_enabled()` evaluation helper."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.db.models import StaffUser
from app.feature_flags.errors import DuplicateFeatureFlagCodeError, FeatureFlagNotFoundError
from app.feature_flags.service import create_flag, get_flag, is_enabled, set_flag_enabled
from sqlalchemy.ext.asyncio import AsyncSession

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def test_create_flag_defaults_to_disabled(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    code = f"test.flag.{uuid.uuid4().hex[:8]}"
    flag = await create_flag(db_session, actor=actor, code=code, name="Test flag", description=None)
    assert flag.is_enabled is False
    assert flag.code == code


async def test_create_flag_rejects_duplicate_code(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    code = f"test.flag.{uuid.uuid4().hex[:8]}"
    await create_flag(db_session, actor=actor, code=code, name="First", description=None)
    with pytest.raises(DuplicateFeatureFlagCodeError):
        await create_flag(db_session, actor=actor, code=code, name="Second", description=None)


async def test_get_flag_raises_for_unknown_id(db_session: AsyncSession) -> None:
    with pytest.raises(FeatureFlagNotFoundError):
        await get_flag(db_session, uuid.uuid4())


async def test_is_enabled_reflects_current_state_and_missing_flag_default(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user()
    code = f"test.flag.{uuid.uuid4().hex[:8]}"
    flag = await create_flag(
        db_session, actor=actor, code=code, name="Toggle me", description=None, is_enabled=False
    )
    assert await is_enabled(db_session, code) is False

    await set_flag_enabled(db_session, flag=flag, actor=actor, is_enabled=True)
    assert await is_enabled(db_session, code) is True

    unknown_code = f"test.flag.never-created.{uuid.uuid4().hex[:8]}"
    assert await is_enabled(db_session, unknown_code, default=True) is True
    assert await is_enabled(db_session, unknown_code, default=False) is False
