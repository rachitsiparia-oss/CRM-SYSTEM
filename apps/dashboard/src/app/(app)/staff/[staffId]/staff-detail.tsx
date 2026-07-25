"use client";

import { useState } from "react";
import Link from "next/link";

import {
  useAssignRole,
  useRemoveRole,
  useSetAccountStatus,
  useStaffDetail,
} from "@/lib/hooks/use-staff";
import { useRoles } from "@/lib/hooks/use-roles";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/errors";

function ReasonPrompt({
  label,
  onConfirm,
  disabled,
}: {
  label: string;
  onConfirm: (reason: string) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");

  if (!open) {
    return (
      <Button variant="outline" size="sm" disabled={disabled} onClick={() => setOpen(true)}>
        {label}
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <input
        className="h-8 rounded-md border border-zinc-300 bg-transparent px-2 text-sm dark:border-zinc-700"
        placeholder="Reason (required)"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <Button
        size="sm"
        disabled={!reason.trim() || disabled}
        onClick={() => {
          onConfirm(reason.trim());
          setOpen(false);
          setReason("");
        }}
      >
        Confirm
      </Button>
      <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
        Cancel
      </Button>
    </div>
  );
}

export function StaffDetail({ staffId }: { staffId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: staff, isLoading, isError } = useStaffDetail(staffId);
  const { data: roles } = useRoles();
  const [actionError, setActionError] = useState<string | null>(null);

  const assignRole = useAssignRole(staffId);
  const removeRole = useRemoveRole(staffId);
  const setAccountStatus = useSetAccountStatus(staffId);

  const [selectedRoleCode, setSelectedRoleCode] = useState("");

  const canManageStaff = hasPermission(currentUser, "staff.manage");
  const canManageRoles = hasPermission(currentUser, "roles.manage");
  const isSelf = currentUser?.id === staffId;

  function handleError(error: unknown) {
    setActionError(error instanceof ApiError ? error.message : "That action could not be completed.");
  }

  if (isLoading) {
    return <div className="p-6 text-sm text-zinc-500">Loading…</div>;
  }
  if (isError || !staff) {
    return <div className="p-6 text-sm text-red-600">Could not load this staff member.</div>;
  }

  const assignedRoleCodes = new Set(staff.roles.map((role) => role.code));
  const availableRoles = (roles ?? []).filter((role) => !assignedRoleCodes.has(role.code));

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link href="/staff" className="text-sm text-zinc-500 hover:underline">
          ← Staff & HR
        </Link>
        <h1 className="mt-2 text-lg font-semibold">{staff.display_name}</h1>
        <p className="text-sm text-zinc-500">
          {staff.employee_code} · {staff.email}
          {staff.job_title ? ` · ${staff.job_title}` : ""}
        </p>
      </div>

      <div className="grid gap-1 text-sm sm:grid-cols-2">
        <div>
          <span className="text-zinc-500">Account status: </span>
          <span className="capitalize">{staff.account_status}</span>
        </div>
        <div>
          <span className="text-zinc-500">Employment status: </span>
          <span className="capitalize">{staff.employment_status.replace("_", " ")}</span>
        </div>
        <div>
          <span className="text-zinc-500">Phone: </span>
          <span>{staff.phone_e164 ?? "Not visible or not set"}</span>
        </div>
        <div>
          <span className="text-zinc-500">Timezone: </span>
          <span>{staff.timezone}</span>
        </div>
      </div>

      {actionError && <p className="text-sm text-red-600">{actionError}</p>}

      {canManageStaff && !isSelf && (
        <div className="flex gap-2">
          {staff.account_status !== "active" ? (
            <ReasonPrompt
              label="Activate account"
              disabled={setAccountStatus.isPending}
              onConfirm={(reason) =>
                setAccountStatus.mutate(
                  { action: "activate", reason },
                  { onError: handleError },
                )
              }
            />
          ) : (
            <ReasonPrompt
              label="Deactivate account"
              disabled={setAccountStatus.isPending}
              onConfirm={(reason) =>
                setAccountStatus.mutate(
                  { action: "deactivate", reason },
                  { onError: handleError },
                )
              }
            />
          )}
        </div>
      )}
      {isSelf && (
        <p className="text-sm text-zinc-500">
          You cannot change your own account status or roles — ask another privileged staff
          member.
        </p>
      )}

      <div>
        <h2 className="mb-2 text-sm font-semibold">Roles</h2>
        <ul className="mb-3 flex flex-wrap gap-2">
          {staff.roles.map((role) => (
            <li
              key={role.id}
              className="flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1 text-sm dark:bg-zinc-800"
            >
              {role.name}
              {canManageRoles && !isSelf && (
                <button
                  type="button"
                  aria-label={`Remove ${role.name}`}
                  className="text-zinc-500 hover:text-red-600"
                  disabled={removeRole.isPending}
                  onClick={() => {
                    const reason = window.prompt(`Reason for removing ${role.name}?`);
                    if (reason) {
                      removeRole.mutate({ roleCode: role.code, reason }, { onError: handleError });
                    }
                  }}
                >
                  ×
                </button>
              )}
            </li>
          ))}
          {staff.roles.length === 0 && <li className="text-sm text-zinc-500">No roles assigned.</li>}
        </ul>

        {canManageRoles && !isSelf && availableRoles.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              className="h-9 rounded-md border border-zinc-300 bg-transparent px-2 text-sm dark:border-zinc-700"
              value={selectedRoleCode}
              onChange={(e) => setSelectedRoleCode(e.target.value)}
            >
              <option value="">Add a role…</option>
              {availableRoles.map((role) => (
                <option key={role.id} value={role.code}>
                  {role.name}
                </option>
              ))}
            </select>
            <Button
              size="sm"
              disabled={!selectedRoleCode || assignRole.isPending}
              onClick={() => {
                const reason = window.prompt(`Reason for assigning this role?`);
                if (reason) {
                  assignRole.mutate(
                    { roleCode: selectedRoleCode, reason },
                    { onError: handleError, onSuccess: () => setSelectedRoleCode("") },
                  );
                }
              }}
            >
              Assign
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
