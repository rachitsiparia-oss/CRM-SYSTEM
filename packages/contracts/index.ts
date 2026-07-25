// Shared API contracts, error shapes, and pagination definitions —
// ARCHITECTURE_AND_TECH_STACK.md section 5.5. Backend types remain
// authoritative; this package must be refreshed through a documented
// process, not hand-duplicated ahead of the backend schema.

export type ErrorCode =
  | "validation_error"
  | "authentication_required"
  | "permission_denied"
  | "not_found"
  | "conflict"
  | "invalid_state_transition"
  | "rate_limited"
  | "external_dependency_unavailable"
  | "integration_configuration_error"
  | "retryable_processing_failure"
  | "internal_error";

export interface ApiErrorBody {
  error: {
    code: ErrorCode;
    message: string;
    field_errors?: Record<string, string[]>;
    request_id: string;
  };
}

export interface Meta {
  request_id: string;
}

export interface DataResponse<T> {
  data: T;
  meta: Meta;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
  meta: Meta;
}

// --- Phase 3: Authentication, Users, Roles, and Permissions ---
// Mirrors apps/api/app/auth/schemas.py, apps/api/app/staff/schemas.py, and
// apps/api/app/roles/schemas.py. Keep these in sync by hand until a
// generation step exists — ARCHITECTURE_AND_TECH_STACK.md section 5.5.

export type AccountStatus = "invited" | "active" | "suspended" | "disabled" | "locked" | "archived";
export type EmploymentStatus = "full_time" | "part_time" | "contract" | "intern";
export type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

export interface RoleRef {
  id: string;
  code: string;
  name: string;
}

export interface CurrentUser {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string | null;
  display_name: string;
  email: string;
  phone_e164: string | null;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
  last_login_at: string | null;
  timezone: string;
  avatar_storage_path: string | null;
  preferred_language: string | null;
  roles: RoleRef[];
  permissions: string[];
}

export interface StaffUserListItem {
  id: string;
  employee_code: string;
  display_name: string;
  email: string;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
}

export interface StaffUserDetail {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string | null;
  display_name: string;
  email: string;
  phone_e164: string | null;
  department_id: string | null;
  job_title: string | null;
  account_status: AccountStatus;
  employment_status: EmploymentStatus;
  is_privileged: boolean;
  last_login_at: string | null;
  timezone: string;
  avatar_storage_path: string | null;
  preferred_language: string | null;
  roles: RoleRef[];
}

export interface Department {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface RoleListItem {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system_role: boolean;
  is_active: boolean;
}

export interface Permission {
  id: string;
  code: string;
  module: string;
  action: string;
  description: string | null;
  is_sensitive: boolean;
}

export interface RolePermissions {
  role: RoleListItem;
  permission_codes: string[];
}

export interface Invitation {
  id: string;
  email: string;
  first_name: string;
  last_name: string | null;
  department_id: string | null;
  intended_role_id: string;
  status: InvitationStatus;
  invited_at: string;
  expires_at: string;
}
