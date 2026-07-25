"""Staff administration business logic — kept out of the router so the
privilege-escalation guards are unit-testable without an HTTP client.

SECURITY_PERFORMANCE_AND_QUALITY.md section 4.4 ("A user must not be able
to... modify their own role without authorization") is enforced here by a
flat rule: nobody may assign or remove their own role, or deactivate their
own account, through these endpoints, regardless of what permissions they
hold. There is no exception for the owner role — an owner who needs their
own access changed must have another privileged user do it, which keeps
every such change attributable to a second party in the audit trail.
"""

import uuid

import httpx
from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.core.config import get_settings
from app.db.models import Role, StaffInvitation, StaffRole, StaffUser
from app.permissions.seed import default_invitation_expiry
from app.permissions.service import invalidate_permissions_cache


async def _send_supabase_invite_email(
    *, email: str, first_name: str, last_name: str | None
) -> None:
    """Creates the (unconfirmed) Supabase Auth user and sends Supabase's
    own "invite user" email — GoTrue's `POST /invite` admin endpoint,
    which `supabase.auth.admin.inviteUserByEmail()` calls under the hood.

    This is a real, previously-missing step: earlier, `create_invitation`
    only wrote our own bookkeeping row and never actually told Supabase to
    email anyone, so no invitation email was ever sent.
    """
    settings = get_settings()
    if not (settings.supabase_url and settings.supabase_service_role_key):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invitations are not configured on this environment.",
        )

    redirect_to = f"{settings.dashboard_base_url}/auth/callback?next=/reset-password"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.supabase_url}/auth/v1/invite",
                params={"redirect_to": redirect_to},
                json={"email": email, "data": {"first_name": first_name, "last_name": last_name}},
                headers={
                    "apikey": settings.supabase_service_role_key,
                    "Authorization": f"Bearer {settings.supabase_service_role_key}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the invitation email. Try again shortly.",
        ) from exc

    if response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already registered with Supabase Auth.",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the invitation email. Try again shortly.",
        )


class SelfModificationError(HTTPException):
    def __init__(self, message: str) -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=message)


async def assign_role(
    session: AsyncSession,
    *,
    actor: StaffUser,
    target: StaffUser,
    role_code: str,
    reason: str,
    request: Request | None,
) -> None:
    if actor.id == target.id:
        raise SelfModificationError("You cannot change your own role assignments.")

    role = await session.scalar(
        select(Role).where(Role.code == role_code, Role.is_active.is_(True))
    )
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown or inactive role."
        )

    existing = await session.scalar(
        select(StaffRole).where(StaffRole.staff_user_id == target.id, StaffRole.role_id == role.id)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Role is already assigned."
        )

    session.add(StaffRole(staff_user_id=target.id, role_id=role.id, assigned_by=actor.id))
    invalidate_permissions_cache(target.id)
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="staff.role_assigned",
        target_type="staff_user",
        target_id=target.id,
        request=request,
        safe_metadata={"role_code": role_code, "reason": reason},
    )


async def remove_role(
    session: AsyncSession,
    *,
    actor: StaffUser,
    target: StaffUser,
    role_code: str,
    reason: str,
    request: Request | None,
) -> None:
    if actor.id == target.id:
        raise SelfModificationError("You cannot change your own role assignments.")

    role = await session.scalar(select(Role).where(Role.code == role_code))
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown role.")

    existing = await session.scalar(
        select(StaffRole).where(StaffRole.staff_user_id == target.id, StaffRole.role_id == role.id)
    )
    if existing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role is not assigned.")

    await session.delete(existing)
    invalidate_permissions_cache(target.id)
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="staff.role_removed",
        target_type="staff_user",
        target_id=target.id,
        request=request,
        safe_metadata={"role_code": role_code, "reason": reason},
    )


async def set_account_status(
    session: AsyncSession,
    *,
    actor: StaffUser,
    target: StaffUser,
    new_status: str,
    reason: str,
    request: Request | None,
) -> None:
    if actor.id == target.id:
        raise SelfModificationError("You cannot activate or deactivate your own account.")

    before_status = target.account_status
    target.account_status = new_status
    target.updated_by = actor.id
    invalidate_permissions_cache(target.id)
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="staff.account_status_changed",
        target_type="staff_user",
        target_id=target.id,
        request=request,
        before_summary={"account_status": before_status},
        after_summary={"account_status": new_status},
        safe_metadata={"reason": reason},
    )


async def create_invitation(
    session: AsyncSession,
    *,
    actor: StaffUser,
    email: str,
    first_name: str,
    last_name: str | None,
    department_id: uuid.UUID | None,
    role_code: str,
    request: Request | None,
) -> StaffInvitation:
    role = await session.scalar(
        select(Role).where(Role.code == role_code, Role.is_active.is_(True))
    )
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown or inactive role."
        )

    existing_user = await session.scalar(
        select(StaffUser).where(StaffUser.email == email, StaffUser.deleted_at.is_(None))
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This email already has a staff account."
        )

    existing_invitation = await session.scalar(
        select(StaffInvitation).where(
            StaffInvitation.email == email, StaffInvitation.status == "pending"
        )
    )
    if existing_invitation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email.",
        )

    # Send the real email before writing our own bookkeeping row — if
    # Supabase can't be reached or refuses the invite, we don't want a
    # StaffInvitation row implying one was sent when it wasn't.
    await _send_supabase_invite_email(email=email, first_name=first_name, last_name=last_name)

    invitation = StaffInvitation(
        id=uuid.uuid4(),
        email=email,
        first_name=first_name,
        last_name=last_name,
        department_id=department_id,
        intended_role_id=role.id,
        invited_by=actor.id,
        status="pending",
        expires_at=default_invitation_expiry(),
    )
    session.add(invitation)
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="staff.invitation_created",
        target_type="staff_invitation",
        target_id=invitation.id,
        request=request,
        safe_metadata={"email": email, "role_code": role_code},
    )
    return invitation
