// Typed API client foundation — ARCHITECTURE_AND_TECH_STACK.md section 5.6.
// This package is always named @rkpr/api-client, never @rkpr/sdk.
//
// Endpoint-specific methods are added as each module's API contract lands
// (DATABASE_AND_API.md sections 20+); Phase 1 only establishes the shared
// request/error-mapping foundation.

import type { ApiErrorBody } from "@rkpr/contracts";

export class ApiError extends Error {
  readonly code: ApiErrorBody["error"]["code"];
  readonly requestId: string;
  readonly fieldErrors?: Record<string, string[]>;

  constructor(body: ApiErrorBody) {
    super(body.error.message);
    this.name = "ApiError";
    this.code = body.error.code;
    this.requestId = body.error.request_id;
    this.fieldErrors = body.error.field_errors;
  }
}

export interface ApiClientOptions {
  baseUrl: string;
  signal?: AbortSignal;
}

export async function apiRequest<T>(
  path: string,
  { baseUrl, signal, ...init }: ApiClientOptions & RequestInit,
): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    signal,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });

  if (!response.ok) {
    const body = (await response.json()) as ApiErrorBody;
    throw new ApiError(body);
  }

  return (await response.json()) as T;
}
