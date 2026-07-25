import type { ApiErrorBody } from "@rkpr/contracts";
import { ApiError } from "./errors";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export interface ApiFetchOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  accessToken?: string | null;
}

/**
 * Shared fetch wrapper for calling the FastAPI backend. Attaches the
 * Supabase access token as a Bearer header (the two apps are on separate
 * origins — Vercel and Railway — so this, not a shared cookie, is how the
 * backend authenticates the request; ARCHITECTURE_AND_TECH_STACK.md
 * section 10.2 prefers cookies for the *browser session*, which
 * @supabase/ssr already provides on the dashboard's own origin).
 */
export async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(0, "external_dependency_unavailable", "API base URL is not configured.");
  }

  const { body, accessToken, headers, ...rest } = options;

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    let parsed: ApiErrorBody | null = null;
    try {
      parsed = (await response.json()) as ApiErrorBody;
    } catch {
      // Non-JSON error body — fall through to the generic error below.
    }
    if (parsed?.error) {
      throw new ApiError(
        response.status,
        parsed.error.code,
        parsed.error.message,
        parsed.error.field_errors,
        parsed.error.request_id,
      );
    }
    throw new ApiError(response.status, "unknown", `Request failed with status ${response.status}.`);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
