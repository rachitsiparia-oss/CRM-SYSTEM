"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { LogOut, MoreHorizontal, RotateCcw, Settings, User as UserIcon } from "lucide-react";

import { createClient } from "@/lib/supabase/client";
import { apiFetchClient } from "@/lib/api/browser";
import { useCurrentUser, currentUserQueryKey } from "@/lib/hooks/use-current-user";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  return (first + last).toUpperCase() || "U";
}

export interface UserMenuProps {
  /** "sidebar" renders the full-width avatar+name+email footer card used at
   * the bottom of the Sidebar (Phase 17.5 redesign); "compact" is the
   * original narrow header trigger, kept for any other call site. */
  variant?: "sidebar" | "compact";
}

export function UserMenu({ variant = "compact" }: UserMenuProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: user, isLoading, isError, refetch } = useCurrentUser();

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

  if (isLoading) {
    return (
      <Skeleton className={variant === "sidebar" ? "h-12 w-full rounded-lg" : "size-9 rounded-full"} />
    );
  }
  if (isError) {
    // The profile call failed (network blip, cold connection) — showing
    // nothing here used to look exactly like being logged out, with no way
    // to tell. A visible retry affordance instead of silence.
    return (
      <Button
        variant="ghost"
        size="icon"
        className="size-9"
        aria-label="Retry loading your profile"
        onClick={() => void refetch()}
      >
        <RotateCcw className="size-4" />
      </Button>
    );
  }
  if (!user) {
    return null;
  }

  const roleLabel = user.roles.map((role) => role.name).join(", ") || "No role assigned";
  const secondaryLine = variant === "sidebar" ? user.email : roleLabel;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className={cn(
            "flex items-center gap-2",
            variant === "sidebar" ? "h-auto w-full justify-start px-2 py-2" : "h-9 px-2",
          )}
          aria-label={`Account menu for ${user.display_name}`}
        >
          <Avatar className="size-7">
            <AvatarFallback className="text-xs">{initials(user.display_name)}</AvatarFallback>
          </Avatar>
          <span className={cn("min-w-0 text-left", variant === "compact" && "hidden sm:block")}>
            <span className="block text-sm leading-none font-medium">{user.display_name}</span>
            <span className="text-muted-foreground mt-1 block truncate text-xs leading-none">
              {secondaryLine}
            </span>
          </span>
          {variant === "sidebar" && (
            <MoreHorizontal className="text-muted-foreground ml-auto size-4 shrink-0" aria-hidden="true" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        side={variant === "sidebar" ? "top" : "bottom"}
        className="w-56"
      >
        <DropdownMenuLabel>
          <span className="block truncate font-medium">{user.display_name}</span>
          <span className="text-muted-foreground block truncate text-xs font-normal">
            {user.email}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/profile">
            <UserIcon />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/settings">
            <Settings />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onSelect={handleLogout}>
          <LogOut />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
