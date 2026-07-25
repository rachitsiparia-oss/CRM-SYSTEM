import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.auth.schemas import RoleOut

EmploymentStatus = Literal["full_time", "part_time", "contract", "intern"]


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    is_active: bool


class StaffUserListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_code: str
    display_name: str
    email: str
    department_id: uuid.UUID | None
    job_title: str | None
    account_status: str
    employment_status: str
    is_privileged: bool


class StaffUserDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_code: str
    first_name: str
    last_name: str | None
    display_name: str
    email: str
    phone_e164: str | None = None
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


class StaffUserAdminUpdateIn(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, max_length=80)
    department_id: uuid.UUID | None = None
    job_title: str | None = Field(default=None, max_length=120)
    phone_e164: str | None = Field(default=None, max_length=20)
    employment_status: EmploymentStatus | None = None


class ProfileUpdateIn(BaseModel):
    phone_e164: str | None = Field(default=None, max_length=20)
    timezone: str | None = Field(default=None, max_length=64)
    preferred_language: str | None = Field(default=None, max_length=16)
    avatar_storage_path: str | None = Field(default=None, max_length=500)


class AccountStatusChangeIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class RoleAssignIn(BaseModel):
    role_code: str
    reason: str = Field(min_length=1, max_length=500)


class InvitationCreateIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    first_name: str = Field(min_length=1, max_length=80)
    # last_name and department_id are nullable at the database level
    # (DATABASE_AND_API.md section 4.6, StaffInvitation still allows both
    # NULL for rows created through other paths) but required here: the
    # invite form requires every field before it can submit, and the
    # backend is the authority on that rule, not just the frontend
    # (CLAUDE.md section 10, "server validation as the authority").
    last_name: str = Field(min_length=1, max_length=80)
    department_id: uuid.UUID
    role_code: str


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    first_name: str
    last_name: str | None
    department_id: uuid.UUID | None
    intended_role_id: uuid.UUID
    status: str
    invited_at: datetime
    expires_at: datetime
