from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.auth.dependencies import CurrentStaffUser
from app.auth.schemas import (
    CurrentUserOut,
    LoginHistoryEntryOut,
    PasswordResetRequestIn,
    RoleOut,
    SessionOut,
)
from app.auth.tokens import decode_access_token
from app.core.config import get_settings
from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.rate_limit import check_rate_limit
from app.core.responses import DataResponse, request_meta
from app.db.models import AuditEvent, Role, StaffRole, StaffUser
from app.db.session import get_db
from app.permissions.service import get_effective_permissions
from app.staff.schemas import ProfileUpdateIn

# The account's own authentication/authorization security history — every
# event a staff member should be able to see about their own account
# without needing an admin permission. auth.password_reset_requested is
# excluded: it's recorded with target_id=None by design (unauthenticated,
# no confirmed identity — SECURITY_PERFORMANCE_AND_QUALITY.md section 3.4's
# enumeration-avoidance rule), so it can never be attributed to one account.
_LOGIN_HISTORY_ACTION_CODES = (
    "auth.login",
    "auth.logout",
    "auth.access_denied",
    "auth.account_locked",
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
_bearer_scheme = HTTPBearer(auto_error=False)


async def _build_current_user_out(session: AsyncSession, staff_user: StaffUser) -> CurrentUserOut:
    roles = (
        await session.scalars(
            select(Role)
            .join(StaffRole, StaffRole.role_id == Role.id)
            .where(StaffRole.staff_user_id == staff_user.id)
        )
    ).all()
    permissions = await get_effective_permissions(session, staff_user.id)
    return CurrentUserOut(
        id=staff_user.id,
        employee_code=staff_user.employee_code,
        first_name=staff_user.first_name,
        last_name=staff_user.last_name,
        display_name=staff_user.display_name,
        email=staff_user.email,
        phone_e164=staff_user.phone_e164,
        department_id=staff_user.department_id,
        job_title=staff_user.job_title,
        account_status=staff_user.account_status,
        employment_status=staff_user.employment_status,
        is_privileged=staff_user.is_privileged,
        last_login_at=staff_user.last_login_at,
        timezone=staff_user.timezone,
        avatar_storage_path=staff_user.avatar_storage_path,
        preferred_language=staff_user.preferred_language,
        roles=[RoleOut.model_validate(role) for role in roles],
        permissions=sorted(permissions),
    )


@router.post("/login")
async def login(
    request: Request,
    staff_user: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CurrentUserOut]:
    """Called once by the frontend immediately after Supabase Auth sign-in
    succeeds. Distinct from GET /me: this endpoint has the side effects of
    a login (updating `last_login_at`, writing the `auth.login` audit
    event) — SECURITY_PERFORMANCE_AND_QUALITY.md section 3.2 ("audit
    history for sign-in")."""
    staff_user.last_login_at = datetime.now(UTC)
    await record_audit_event(
        session,
        actor_id=staff_user.id,
        action_code="auth.login",
        target_type="staff_user",
        target_id=staff_user.id,
        request=request,
    )
    out = await _build_current_user_out(session, staff_user)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/me")
async def me(
    request: Request,
    staff_user: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CurrentUserOut]:
    out = await _build_current_user_out(session, staff_user)
    return DataResponse(data=out, meta=request_meta(request))


@router.patch("/me")
async def update_my_profile(
    request: Request,
    payload: ProfileUpdateIn,
    staff_user: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CurrentUserOut]:
    """Self-service profile fields only. Email, department, role,
    employment status, and account status can only be changed by an admin
    through /api/v1/staff-users/{id} — SECURITY_PERFORMANCE_AND_QUALITY.md
    section 4.4 ("must not... modify their own role without
    authorization")."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(staff_user, field, value)
    if updates:
        await record_audit_event(
            session,
            actor_id=staff_user.id,
            action_code="staff.profile_updated",
            target_type="staff_user",
            target_id=staff_user.id,
            request=request,
            safe_metadata={"fields": sorted(updates.keys())},
        )
    out = await _build_current_user_out(session, staff_user)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/logout")
async def logout(
    request: Request,
    staff_user: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    """Records the logout for audit purposes. Actual token/session
    invalidation happens client-side via the Supabase client's own
    `signOut()`, which revokes the refresh token at Supabase —
    ARCHITECTURE_AND_TECH_STACK.md section 10.2."""
    await record_audit_event(
        session,
        actor_id=staff_user.id,
        action_code="auth.logout",
        target_type="staff_user",
        target_id=staff_user.id,
        request=request,
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.get("/session")
async def session_info(
    request: Request,
    _staff_user: CurrentStaffUser,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> DataResponse[SessionOut]:
    """Read-only session metadata decoded from the verified token — no
    separate sessions table is maintained; Supabase Auth owns session
    storage (ARCHITECTURE_AND_TECH_STACK.md section 9.2)."""
    assert credentials is not None  # guaranteed by get_current_staff_user succeeding above
    claims = decode_access_token(credentials.credentials)
    out = SessionOut(
        auth_user_id=claims.auth_user_id,
        session_id=claims.session_id,
        issued_at=datetime.fromtimestamp(claims.issued_at, tz=UTC) if claims.issued_at else None,
        expires_at=datetime.fromtimestamp(claims.expires_at, tz=UTC) if claims.expires_at else None,
    )
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/login-history")
async def login_history(
    request: Request,
    staff_user: CurrentStaffUser,
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
) -> PaginatedResponse[LoginHistoryEntryOut]:
    """The caller's own authentication/authorization security history —
    logins, logouts, access-denied rejections, and account-lock events.
    Self-service only (no permission code): every staff member can see
    their own security history, no admin authority required, and this
    never returns another account's events."""
    base_filter = (
        AuditEvent.target_type == "staff_user",
        AuditEvent.target_id == staff_user.id,
        AuditEvent.action_code.in_(_LOGIN_HISTORY_ACTION_CODES),
    )
    total = await session.scalar(select(func.count()).select_from(AuditEvent).where(*base_filter))
    stmt = (
        select(AuditEvent)
        .where(*base_filter)
        .order_by(AuditEvent.created_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    data = [LoginHistoryEntryOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(
            page=page_params.page, page_size=page_params.page_size, total=total or 0
        ),
        meta=request_meta(request),
    )


@router.post("/password-reset")
async def request_password_reset(
    request: Request,
    payload: PasswordResetRequestIn,
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    """Unauthenticated by design — the caller has just forgotten their
    password. Proxies to Supabase Auth's own recovery endpoint (rather than
    the frontend calling it directly) so the attempt is rate-limited and
    audited here — SECURITY_PERFORMANCE_AND_QUALITY.md section 3.4
    ("secure recovery tokens", "rate limiting by IP and account
    identifier"). Always returns the same generic response regardless of
    whether the email exists, to avoid account enumeration.
    """
    client_host = request.client.host if request.client else "unknown"
    email_key = payload.email.strip().lower()
    allowed = await check_rate_limit(
        f"pwreset:{email_key}", limit=3, window_seconds=900
    ) and await check_rate_limit(f"pwreset:ip:{client_host}", limit=10, window_seconds=900)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again shortly.",
        )

    settings = get_settings()
    if settings.supabase_url and settings.supabase_service_role_key:
        redirect_to = f"{settings.dashboard_base_url}/auth/callback?next=/reset-password"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{settings.supabase_url}/auth/v1/recover",
                    params={"redirect_to": redirect_to},
                    json={"email": payload.email},
                    headers={
                        "apikey": settings.supabase_service_role_key,
                        "Content-Type": "application/json",
                    },
                )
        except httpx.HTTPError:
            pass  # never leak provider errors to the caller; response stays generic

    await record_audit_event(
        session,
        actor_id=None,
        action_code="auth.password_reset_requested",
        target_type="staff_user",
        target_id=None,
        request=request,
        safe_metadata={"email_domain": email_key.rsplit("@", 1)[-1] if "@" in email_key else None},
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))
