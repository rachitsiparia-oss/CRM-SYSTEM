"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { LogOut, Settings, User as UserIcon } from "lucide-react";

import { createClient } from "@/lib/supabase/client";
import { apiFetchClient } from "@/lib/api/browser";
import { useCurrentUser, currentUserQueryKey } from "@/lib/hooks/use-current-user";
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

  if (isLoading) {
    return <Skeleton className="size-9 rounded-full" />;
  }
  if (!user) {
    return null;
  }

  const roleLabel = user.roles.map((role) => role.name).join(", ") || "No role assigned";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex h-9 items-center gap-2 px-2"
          aria-label={`Account menu for ${user.display_name}`}
        >
          <Avatar className="size-7">
            <AvatarFallback className="text-xs">{initials(user.display_name)}</AvatarFallback>
          </Avatar>
          <span className="hidden text-left sm:block">
            <span className="block text-sm leading-none font-medium">{user.display_name}</span>
            <span className="text-muted-foreground block text-xs leading-none">{roleLabel}</span>
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
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
