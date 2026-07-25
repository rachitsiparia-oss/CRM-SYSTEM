import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.auth.schemas import RoleOut
from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import Department, Role, StaffRole, StaffUser
from app.db.models.staff_user import ACCOUNT_STATUSES
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.permissions.service import has_permission
from app.staff.schemas import (
    AccountStatusChangeIn,
    DepartmentOut,
    InvitationCreateIn,
    InvitationOut,
    RoleAssignIn,
    StaffUserAdminUpdateIn,
    StaffUserDetailOut,
    StaffUserListItemOut,
)
from app.staff.service import assign_role, create_invitation, remove_role, set_account_status

router = APIRouter(prefix="/api/v1", tags=["staff"])

_SORT_ALLOWLIST = {"display_name", "employee_code", "created_at"}


async def _to_detail_out(
    session: AsyncSession, staff_user: StaffUser, *, viewer: StaffUser
) -> StaffUserDetailOut:
    roles = (
        await session.scalars(
            select(Role)
            .join(StaffRole, StaffRole.role_id == Role.id)
            .where(StaffRole.staff_user_id == staff_user.id)
        )
    ).all()

    can_read_sensitive = viewer.id == staff_user.id or await has_permission(
        session, viewer.id, "staff.hr_sensitive.read"
    )

    return StaffUserDetailOut(
        id=staff_user.id,
        employee_code=staff_user.employee_code,
        first_name=staff_user.first_name,
        last_name=staff_user.last_name,
        display_name=staff_user.display_name,
        email=staff_user.email,
        phone_e164=staff_user.phone_e164 if can_read_sensitive else None,
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
    )


async def _get_target_or_404(session: AsyncSession, staff_user_id: uuid.UUID) -> StaffUser:
    target = await session.scalar(
        select(StaffUser).where(StaffUser.id == staff_user_id, StaffUser.deleted_at.is_(None))
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found.")
    return target


@router.get("/staff-users")
async def list_staff_users(
    request: Request,
    _staff_user: StaffUser = Depends(require_permission("staff.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
    department_id: uuid.UUID | None = Query(default=None),
    account_status: str | None = Query(default=None),
    sort: str = Query(default="display_name"),
) -> PaginatedResponse[StaffUserListItemOut]:
    if sort not in _SORT_ALLOWLIST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort column."
        )
    if account_status is not None and account_status not in ACCOUNT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown account_status filter."
        )

    stmt = select(StaffUser).where(StaffUser.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(StaffUser).where(StaffUser.deleted_at.is_(None))

    if search:
        pattern = f"%{search}%"
        clause = (StaffUser.display_name.ilike(pattern)) | (StaffUser.email.ilike(pattern))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if department_id is not None:
        stmt = stmt.where(StaffUser.department_id == department_id)
        count_stmt = count_stmt.where(StaffUser.department_id == department_id)
    if account_status is not None:
        stmt = stmt.where(StaffUser.account_status == account_status)
        count_stmt = count_stmt.where(StaffUser.account_status == account_status)

    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(getattr(StaffUser, sort))
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()

    data = [StaffUserListItemOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/staff-users/{staff_user_id}")
async def get_staff_user(
    request: Request,
    staff_user_id: uuid.UUID,
    viewer: StaffUser = Depends(require_permission("staff.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffUserDetailOut]:
    target = await _get_target_or_404(session, staff_user_id)
    out = await _to_detail_out(session, target, viewer=viewer)
    return DataResponse(data=out, meta=request_meta(request))


@router.patch("/staff-users/{staff_user_id}")
async def update_staff_user(
    request: Request,
    staff_user_id: uuid.UUID,
    payload: StaffUserAdminUpdateIn,
    actor: StaffUser = Depends(require_permission("staff.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffUserDetailOut]:
    target = await _get_target_or_404(session, staff_user_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(target, field, value)
    if updates:
        target.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="staff.profile_updated",
            target_type="staff_user",
            target_id=target.id,
            request=request,
            safe_metadata={"fields": sorted(updates.keys()), "updated_by_admin": True},
        )
    out = await _to_detail_out(session, target, viewer=actor)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/staff-users/{staff_user_id}/activate")
async def activate_staff_user(
    request: Request,
    staff_user_id: uuid.UUID,
    payload: AccountStatusChangeIn,
    actor: StaffUser = Depends(require_permission("staff.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffUserDetailOut]:
    target = await _get_target_or_404(session, staff_user_id)
    await set_account_status(
        session,
        actor=actor,
        target=target,
        new_status="active",
        reason=payload.reason,
        request=request,
    )
    out = await _to_detail_out(session, target, viewer=actor)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/staff-users/{staff_user_id}/deactivate")
async def deactivate_staff_user(
    request: Request,
    staff_user_id: uuid.UUID,
    payload: AccountStatusChangeIn,
    actor: StaffUser = Depends(require_permission("staff.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffUserDetailOut]:
    target = await _get_target_or_404(session, staff_user_id)
    await set_account_status(
        session,
        actor=actor,
        target=target,
        new_status="disabled",
        reason=payload.reason,
        request=request,
    )
    out = await _to_detail_out(session, target, viewer=actor)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/staff-users/{staff_user_id}/roles", status_code=status.HTTP_201_CREATED)
async def assign_staff_role(
    request: Request,
    staff_user_id: uuid.UUID,
    payload: RoleAssignIn,
    actor: StaffUser = Depends(require_permission("roles.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffUserDetailOut]:
    target = await _get_target_or_404(session, staff_user_id)
    await assign_role(
        session,
        actor=actor,
        target=target,
        role_code=payload.role_code,
        reason=payload.reason,
        request=request,
    )
    out = await _to_detail_out(session, target, viewer=actor)
    return DataResponse(data=out, meta=request_meta(request))


@router.delete("/staff-users/{staff_user_id}/roles/{role_code}")
async def remove_staff_role(
    request: Request,
    staff_user_id: uuid.UUID,
    role_code: str,
    reason: str = Query(min_length=1, max_length=500),
    actor: StaffUser = Depends(require_permission("roles.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StaffUserDetailOut]:
    target = await _get_target_or_404(session, staff_user_id)
    await remove_role(
        session,
        actor=actor,
        target=target,
        role_code=role_code,
        reason=reason,
        request=request,
    )
    out = await _to_detail_out(session, target, viewer=actor)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/staff-invitations", status_code=status.HTTP_201_CREATED)
async def invite_staff_user(
    request: Request,
    payload: InvitationCreateIn,
    actor: StaffUser = Depends(require_permission("staff.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[InvitationOut]:
    invitation = await create_invitation(
        session,
        actor=actor,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        department_id=payload.department_id,
        role_code=payload.role_code,
        request=request,
    )
    out = InvitationOut.model_validate(invitation)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/departments")
async def list_departments(
    request: Request,
    _actor: StaffUser = Depends(require_permission("staff.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[DepartmentOut]]:
    departments = (
        await session.scalars(
            select(Department).where(Department.is_active.is_(True)).order_by(Department.name)
        )
    ).all()
    data = [DepartmentOut.model_validate(department) for department in departments]
    return DataResponse(data=data, meta=request_meta(request))
