"use client";

import { PageHeader } from "@/components/page-header";
import { useCurrentUser } from "@/lib/hooks/use-current-user";
import { Skeleton } from "@/components/ui/skeleton";
import { ProfileForm } from "./profile-form";

export default function ProfilePage() {
  const { data: user, isLoading } = useCurrentUser();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="My Profile"
        description="Update your own contact details. Name, email, department, and role can only be changed by an administrator."
      />
      {isLoading || !user ? (
        <div className="flex max-w-md flex-col gap-4">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>
      ) : (
        <ProfileForm user={user} />
      )}
    </div>
  );
}
