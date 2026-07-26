"use client";

import type { ReactNode } from "react";
import { useCurrentUser, hasPermission } from "@/lib/hooks/use-current-user";
import { ErrorState } from "@/components/error-state";

/**
 * Page-level permission check for usability only — the backend is what
 * actually enforces this (ARCHITECTURE_AND_TECH_STACK.md section 6.9,
 * "the frontend may hide unavailable routes and actions for usability, but
 * the backend must enforce every permission"). Every endpoint this gate
 * protects independently re-checks the same permission server-side.
 */
export function PermissionGate({
  permission,
  children,
}: {
  permission: string;
  children: ReactNode;
}) {
  const { data: user, isLoading, isError, refetch } = useCurrentUser();

  if (isLoading) {
    return <div className="p-6 text-sm text-zinc-500">Loading…</div>;
  }

  // Distinct from "not permitted": the profile couldn't be loaded at all
  // (network blip, cold connection). Showing the same "no access" message
  // here would misrepresent a temporary failure as a real permission
  // denial — retry gets you back in without a full page reload.
  if (isError) {
    return (
      <div className="p-6">
        <ErrorState
          variant="500"
          title="Couldn't verify your access"
          description="Your profile couldn't be loaded. This is usually temporary."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  if (!hasPermission(user, permission)) {
    return (
      <div className="p-6">
        <h1 className="mb-2 text-lg font-semibold">You don&apos;t have access to this</h1>
        <p className="text-sm text-zinc-500">
          This page requires the <code className="font-mono">{permission}</code> permission.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
