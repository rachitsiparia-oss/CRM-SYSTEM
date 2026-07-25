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

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
}
