import uuid

from pydantic import BaseModel, ConfigDict


class RoleListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_system_role: bool
    is_active: bool


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    module: str
    action: str
    description: str | None
    is_sensitive: bool


class RolePermissionsOut(BaseModel):
    role: RoleListItemOut
    permission_codes: list[str]
