import { createBrowserClient } from "@supabase/ssr";

/**
 * Browser-side Supabase client — session lives in cookies via @supabase/ssr,
 * not localStorage (ARCHITECTURE_AND_TECH_STACK.md section 10.2, "no
 * tokens in localStorage when avoidable"). Only the anon key is used here;
 * it is safe-by-design for the browser (DEPLOYMENT_AND_ENV.md section 6.1).
 */
export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  );
}
