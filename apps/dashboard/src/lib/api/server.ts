import { createClient } from "@/lib/supabase/server";
import { apiFetch, type ApiFetchOptions } from "./fetch";

/** Server Component / Server Function variant — reads the access token
 * from the server-side Supabase client (cookie-backed). */
export async function apiFetchServer<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  return apiFetch<T>(path, { ...options, accessToken: session?.access_token ?? null });
}
