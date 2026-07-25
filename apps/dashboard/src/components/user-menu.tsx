"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { createClient } from "@/lib/supabase/client";
import { apiFetchClient } from "@/lib/api/browser";
import { useCurrentUser, currentUserQueryKey } from "@/lib/hooks/use-current-user";
import { Button } from "@/components/ui/button";

export function UserMenu() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: user, isLoading } = useCurrentUser();

  async function handleLogout() {
    try {
      await apiFetchClient("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Still sign out locally even if the audit call failed.
    }
    const supabase = createClient();
    await supabase.auth.signOut();
    queryClient.removeQueries({ queryKey: currentUserQueryKey });
    router.replace("/login");
    router.refresh();
  }

  if (isLoading || !user) {
    return null;
  }

  return (
    <div className="flex items-center gap-3">
      <div className="text-right">
        <p className="text-sm font-medium leading-none">{user.display_name}</p>
        <p className="text-xs text-zinc-500">
          {user.roles.map((role) => role.name).join(", ") || "No role assigned"}
        </p>
      </div>
      <Button variant="outline" size="sm" onClick={handleLogout}>
        Sign out
      </Button>
    </div>
  );
}
