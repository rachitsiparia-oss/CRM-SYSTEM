import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import DataResponse, request_meta
from app.db.models import Permission, Role, RolePermission, StaffUser
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.roles.schemas import PermissionOut, RoleListItemOut, RolePermissionsOut

router = APIRouter(prefix="/api/v1", tags=["roles"])


@router.get("/roles")
async def list_roles(
    request: Request,
    _actor: StaffUser = Depends(require_permission("roles.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[RoleListItemOut]]:
    roles = (await session.scalars(select(Role).order_by(Role.name))).all()
    data = [RoleListItemOut.model_validate(role) for role in roles]
    return DataResponse(data=data, meta=request_meta(request))


@router.get("/roles/{role_id}/permissions")
async def get_role_permissions(
    request: Request,
    role_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("roles.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RolePermissionsOut]:
    role = await session.scalar(select(Role).where(Role.id == role_id))
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")

    codes = (
        await session.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id, RolePermission.scope_type != "none")
            .order_by(Permission.code)
        )
    ).all()
    out = RolePermissionsOut(
        role=RoleListItemOut.model_validate(role), permission_codes=list(codes)
    )
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/permissions")
async def list_permissions(
    request: Request,
    _actor: StaffUser = Depends(require_permission("roles.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[PermissionOut]]:
    permissions = (await session.scalars(select(Permission).order_by(Permission.code))).all()
    data = [PermissionOut.model_validate(permission) for permission in permissions]
    return DataResponse(data=data, meta=request_meta(request))
