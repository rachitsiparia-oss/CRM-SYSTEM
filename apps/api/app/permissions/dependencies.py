"""`require_permission()` — the FastAPI dependency every protected router
uses to enforce the capability registry
(SECURITY_PERFORMANCE_AND_QUALITY.md section 4.1, "Authorization is
capability-based"). There is no role-name shortcut and no `is_privileged`
bypass: every check, including the owner's, goes through the same
role -> role_permissions -> permissions chain, so a role's actual grants
are always what is enforced, not an assumption about which role should
have access.
"""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentStaffUser
from app.db.models import StaffUser
from app.db.session import get_db
from app.permissions.registry import PERMISSION_CODES
from app.permissions.service import has_permission


def require_permission(
    permission_code: str,
) -> Callable[..., Coroutine[Any, Any, StaffUser]]:
    if permission_code not in PERMISSION_CODES:
        raise RuntimeError(
            f"require_permission() used with an unknown permission code: {permission_code!r}. "
            "Add it to app.permissions.registry first — do not invent a synonym."
        )

    async def _dependency(
        staff_user: CurrentStaffUser,
        session: AsyncSession = Depends(get_db),
    ) -> StaffUser:
        allowed = await has_permission(session, staff_user.id, permission_code)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return staff_user

    return _dependency
