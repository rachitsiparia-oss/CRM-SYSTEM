import { DashboardShell } from "@/components/layout/dashboard-shell";

// Every page under this segment is authenticated, cookie-gated content
// whose real body comes entirely from client-side fetches (TanStack Query)
// behind Supabase auth — nothing here is knowable at build time, so it
// should never be treated as static. (This alone did not fix the "stuck on
// the loading skeleton" bug below — see the now-deleted loading.tsx for
// that — but auth-gated content still has no business being statically
// prerendered, so it stays.)
export const dynamic = "force-dynamic";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <DashboardShell>{children}</DashboardShell>;
}
