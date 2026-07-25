import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

/**
 * Server-side Supabase client for Server Components, Server Functions, and
 * Route Handlers. `setAll` is wrapped in try/catch because Server
 * Components cannot write cookies (Next.js docs: "Setting cookies is not
 * supported during Server Component rendering") — the proxy is what keeps
 * the session refreshed in that case; see src/proxy.ts.
 */
export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Called from a Server Component — ignored, the proxy refreshes
            // the session on the next request instead.
          }
        },
      },
    },
  );
}
