"use client";

import { useState } from "react";
import Link from "next/link";

import { useRolePermissions, useRoles } from "@/lib/hooks/use-roles";

export function RolesViewer() {
  const { data: roles, isLoading } = useRoles();
  const [selectedRoleId, setSelectedRoleId] = useState<string | undefined>();
  const { data: rolePermissions, isLoading: isLoadingPermissions } =
    useRolePermissions(selectedRoleId);

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <div>
        <Link href="/staff" className="text-sm text-muted-foreground hover:underline">
          ← Staff & HR
        </Link>
        <h1 className="mt-2 text-lg font-semibold">Roles & permissions</h1>
        <p className="text-sm text-muted-foreground">
          The 15 system roles and the capability registry each one grants —
          DATABASE_AND_API.md §4.3-4.4.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-[280px_1fr]">
        <ul className="flex flex-col gap-1">
          {isLoading && <li className="text-sm text-muted-foreground">Loading…</li>}
          {roles?.map((role) => (
            <li key={role.id}>
              <button
                type="button"
                onClick={() => setSelectedRoleId(role.id)}
                className={`w-full rounded-md px-3 py-2 text-left text-sm ${
                  selectedRoleId === role.id
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                {role.name}
                {!role.is_active && " (inactive)"}
              </button>
            </li>
          ))}
        </ul>

        <div>
          {!selectedRoleId && (
            <p className="text-sm text-muted-foreground">Select a role to view its permissions.</p>
          )}
          {selectedRoleId && isLoadingPermissions && (
            <p className="text-sm text-muted-foreground">Loading permissions…</p>
          )}
          {rolePermissions && (
            <div>
              <h2 className="mb-1 text-sm font-semibold">{rolePermissions.role.name}</h2>
              {rolePermissions.role.description && (
                <p className="mb-3 text-sm text-muted-foreground">{rolePermissions.role.description}</p>
              )}
              <p className="mb-2 text-xs text-muted-foreground">
                {rolePermissions.permission_codes.length} permission
                {rolePermissions.permission_codes.length === 1 ? "" : "s"}
              </p>
              <ul className="flex flex-wrap gap-1.5">
                {rolePermissions.permission_codes.map((code) => (
                  <li
                    key={code}
                    className="rounded-md bg-muted px-2 py-1 font-mono text-xs"
                  >
                    {code}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
