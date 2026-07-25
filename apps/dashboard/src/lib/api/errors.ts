import type { ErrorCode } from "@rkpr/contracts";

/** Mirrors DATABASE_AND_API.md section 19.4's standard error shape. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: ErrorCode | "unknown";
  readonly fieldErrors: Record<string, string[]> | undefined;
  readonly requestId: string | undefined;

  constructor(
    status: number,
    code: ErrorCode | "unknown",
    message: string,
    fieldErrors?: Record<string, string[]>,
    requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fieldErrors = fieldErrors;
    this.requestId = requestId;
  }
}
