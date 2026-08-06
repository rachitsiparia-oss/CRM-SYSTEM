"""`require_permission()` — the FastAPI dependency every protected router
uses to enforce the capability registry
(SECURITY_PERFORMANCE_AND_QUALITY.md section 4.1, "Authorization is
capability-based"). There is no role-name shortcut and no `is_privileged`
bypass: every check, including the owner's, goes through the same
role -> role_permissions -> permissions chain, so a role's actual grants
are always what is enforced, not an assumption about which role should
have access.

Phase 16 hardening: repeated permission denials for the same staff account
are a signal worth acting on — a compromised session or a malicious/buggy
client probing for access it doesn't have. `_PERMISSION_DENIAL_LIMIT`
denials within `_PERMISSION_DENIAL_WINDOW_SECONDS` auto-locks the account
(`account_status = "locked"`, already an enforced status —
`app.auth.dependencies.get_current_staff_user` rejects it — and already
reversible by an admin via `PATCH /staff/{id}/status`, so this reuses an
existing control rather than inventing a new one). Reuses
`app.core.rate_limit.check_rate_limit`'s per-key counter, which now
applies progressive backoff on its own (see that module), rather than a
second bespoke counter.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.auth.dependencies import CurrentStaffUser
from app.core.rate_limit import check_rate_limit
from app.db.models import StaffUser
from app.db.session import get_db
from app.permissions.registry import PERMISSION_CODES
from app.permissions.service import has_permission, invalidate_permissions_cache

_PERMISSION_DENIAL_LIMIT = 10
_PERMISSION_DENIAL_WINDOW_SECONDS = 300


async def _record_denial_and_maybe_lock(
    session: AsyncSession, *, staff_user: StaffUser, permission_code: str, request: Request
) -> None:
    within_limit = check_rate_limit(
        f"permdenied:{staff_user.id}",
        limit=_PERMISSION_DENIAL_LIMIT,
        window_seconds=_PERMISSION_DENIAL_WINDOW_SECONDS,
    )
    if within_limit or staff_user.account_status == "locked":
        return
    before_status = staff_user.account_status
    staff_user.account_status = "locked"
    await invalidate_permissions_cache(staff_user.id)
    await record_audit_event(
        session,
        actor_id=None,
        action_code="auth.account_locked",
        target_type="staff_user",
        target_id=staff_user.id,
        request=request,
        before_summary={"account_status": before_status},
        after_summary={"account_status": "locked"},
        safe_metadata={
            "reason": "permission_denial_threshold_exceeded",
            "denied_permission_code": permission_code,
            "threshold": _PERMISSION_DENIAL_LIMIT,
            "window_seconds": _PERMISSION_DENIAL_WINDOW_SECONDS,
        },
    )
    # app.db.session.get_db rolls back the whole request transaction on any
    # exception, and the 403 this triggers always raises right after — so
    # without an explicit commit here, the lock itself would be undone by
    # the very rollback it exists to survive.
    await session.commit()


def require_permission(
    permission_code: str,
) -> Callable[..., Coroutine[Any, Any, StaffUser]]:
    if permission_code not in PERMISSION_CODES:
        raise RuntimeError(
            f"require_permission() used with an unknown permission code: {permission_code!r}. "
            "Add it to app.permissions.registry first — do not invent a synonym."
        )

    async def _dependency(
        request: Request,
        staff_user: CurrentStaffUser,
        session: AsyncSession = Depends(get_db),
    ) -> StaffUser:
        allowed = await has_permission(session, staff_user.id, permission_code)
        if not allowed:
            await _record_denial_and_maybe_lock(
                session, staff_user=staff_user, permission_code=permission_code, request=request
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return staff_user

    return _dependency
