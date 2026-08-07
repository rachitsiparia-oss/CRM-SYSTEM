"""Authentication dependency — resolves a verified Supabase access token to
an internal `StaffUser`, enforcing account status
(SECURITY_PERFORMANCE_AND_QUALITY.md section 3.6) and provisioning staff
records on first login from a pending invitation
(DATABASE_AND_API.md section 4.6).
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.auth.tokens import TokenValidationError, decode_access_token
from app.core.rate_limit import check_rate_limit
from app.db.models import StaffInvitation, StaffRole, StaffUser
from app.db.models.staff_user import INACTIVE_ACCOUNT_STATUSES
from app.db.session import get_db

_bearer_scheme = HTTPBearer(auto_error=False)

_INVALID_TOKEN_DETAIL = "Authentication required."


async def _provision_from_invitation(
    session: AsyncSession, *, auth_user_id: uuid.UUID, email: str | None
) -> StaffUser | None:
    if not email:
        return None

    invitation = await session.scalar(
        select(StaffInvitation)
        .where(StaffInvitation.email == email, StaffInvitation.status == "pending")
        .order_by(StaffInvitation.invited_at.desc())
    )
    if invitation is None:
        return None

    now = datetime.now(UTC)
    if invitation.expires_at < now:
        invitation.status = "expired"
        return None

    staff_user = StaffUser(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
        employee_code=f"EMP-{uuid.uuid4().hex[:8].upper()}",
        first_name=invitation.first_name,
        last_name=invitation.last_name,
        display_name=f"{invitation.first_name} {invitation.last_name or ''}".strip(),
        email=email,
        department_id=invitation.department_id,
        account_status="active",
        employment_status="full_time",
        created_by=invitation.invited_by,
    )
    session.add(staff_user)
    await session.flush()

    session.add(
        StaffRole(
            staff_user_id=staff_user.id,
            role_id=invitation.intended_role_id,
            assigned_by=invitation.invited_by,
            assigned_at=now,
        )
    )
    invitation.status = "accepted"
    invitation.accepted_at = now
    invitation.staff_user_id = staff_user.id

    await record_audit_event(
        session,
        actor_id=invitation.invited_by,
        action_code="staff.invitation_accepted",
        target_type="staff_user",
        target_id=staff_user.id,
        safe_metadata={"invitation_id": str(invitation.id)},
    )
    return staff_user


async def get_current_staff_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> StaffUser:
    client_host = request.client.host if request.client else "unknown"
    # 1200/60s (20 req/s), not 60/60s: this check runs on every authenticated
    # request from every staff member sharing one office IP, before the
    # token is even decoded — Phase 17 load testing against a realistic
    # concurrent-VU profile found the original 60/60s threshold throttling
    # entirely legitimate multi-staff traffic (a single dashboard page load
    # alone can fire several API calls). A first pass raised this to
    # 600/60s (10 req/s), but that landed exactly on a k6 profile's own
    # steady-state rate (10 VUs, ~1 req/s each) with no headroom, so any
    # timing jitter tripped one violation — which then blocks every
    # request for the rest of the progressive-backoff penalty, cascading
    # into an outsized failure rate. 1200/60s keeps a real margin above
    # that steady-state while remaining a meaningful bound against
    # unauthenticated flooding — an attacker needs no valid token to trip
    # it either way.
    if not await check_rate_limit(f"auth:{client_host}", limit=1200, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again shortly.",
        )

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN_DETAIL)

    try:
        claims = decode_access_token(credentials.credentials)
    except TokenValidationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=_INVALID_TOKEN_DETAIL
        ) from None

    auth_user_id = uuid.UUID(claims.auth_user_id)

    staff_user = await session.scalar(
        select(StaffUser).where(
            StaffUser.auth_user_id == auth_user_id, StaffUser.deleted_at.is_(None)
        )
    )

    if staff_user is None:
        staff_user = await _provision_from_invitation(
            session, auth_user_id=auth_user_id, email=claims.email
        )

    if staff_user is None:
        await record_audit_event(
            session,
            actor_id=None,
            action_code="auth.access_denied",
            target_type="staff_user",
            target_id=None,
            request=request,
            safe_metadata={"reason": "not_provisioned", "auth_user_id": str(auth_user_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is not provisioned for CRM access.",
        )

    if staff_user.account_status in INACTIVE_ACCOUNT_STATUSES:
        await record_audit_event(
            session,
            actor_id=staff_user.id,
            action_code="auth.access_denied",
            target_type="staff_user",
            target_id=staff_user.id,
            request=request,
            safe_metadata={
                "reason": "inactive_account_status",
                "status": staff_user.account_status,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not have active access.",
        )

    return staff_user


CurrentStaffUser = Annotated[StaffUser, Depends(get_current_staff_user)]
