import { createClient } from "@/lib/supabase/client";
import { apiFetch, type ApiFetchOptions } from "./fetch";

/** Client Component variant, for TanStack Query hooks — reads the access
 * token from the browser Supabase client (also cookie-backed via
 * @supabase/ssr, never localStorage). */
export async function apiFetchClient<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return apiFetch<T>(path, { ...options, accessToken: session?.access_token ?? null });
}
