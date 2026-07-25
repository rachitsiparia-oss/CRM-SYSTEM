import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str


class CurrentUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str | None
    display_name: str
    email: str
    phone_e164: str | None
    department_id: uuid.UUID | None
    job_title: str | None
    account_status: str
    employment_status: str
    is_privileged: bool
    last_login_at: datetime | None
    timezone: str
    avatar_storage_path: str | None
    preferred_language: str | None
    roles: list[RoleOut]
    permissions: list[str]


class SessionOut(BaseModel):
    auth_user_id: str
    session_id: str | None
    issued_at: datetime | None
    expires_at: datetime | None


class PasswordResetRequestIn(BaseModel):
    email: str
