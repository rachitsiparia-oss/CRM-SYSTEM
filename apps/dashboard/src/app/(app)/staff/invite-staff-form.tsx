"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { Department } from "@rkpr/contracts";

import { useInviteStaff } from "@/lib/hooks/use-staff";
import { useRoles } from "@/lib/hooks/use-roles";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/errors";

const inviteSchema = z.object({
  email: z.string().min(1, "Email is required").email("Enter a valid email address."),
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  departmentId: z.string().min(1, "Select a department"),
  roleCode: z.string().min(1, "Select a role"),
});
type InviteValues = z.infer<typeof inviteSchema>;

export function InviteStaffForm({
  departments,
  onDone,
}: {
  departments: Department[];
  onDone: () => void;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const { data: roles } = useRoles();
  const inviteMutation = useInviteStaff();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<InviteValues>({ resolver: zodResolver(inviteSchema) });

  async function onSubmit(values: InviteValues) {
    setFormError(null);
    setSuccess(null);
    try {
      await inviteMutation.mutateAsync({
        email: values.email,
        firstName: values.firstName,
        lastName: values.lastName,
        departmentId: values.departmentId,
        roleCode: values.roleCode,
      });
      setSuccess(`Invitation sent to ${values.email}.`);
      reset();
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "Could not send the invitation.");
    }
  }

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      className="grid gap-3 rounded-md border border-black/10 p-4 dark:border-white/15 sm:grid-cols-2"
      noValidate
    >
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invite-email">
          Email <span className="text-destructive">*</span>
        </Label>
        <Input id="invite-email" type="email" required {...register("email")} />
        {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invite-role">
          Role <span className="text-destructive">*</span>
        </Label>
        <select
          id="invite-role"
          className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
          {...register("roleCode")}
          defaultValue=""
        >
          <option value="" disabled>
            Select a role
          </option>
          {roles?.map((role) => (
            <option key={role.id} value={role.code}>
              {role.name}
            </option>
          ))}
        </select>
        {errors.roleCode && <p className="text-sm text-destructive">{errors.roleCode.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invite-first-name">
          First name <span className="text-destructive">*</span>
        </Label>
        <Input id="invite-first-name" required {...register("firstName")} />
        {errors.firstName && <p className="text-sm text-destructive">{errors.firstName.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invite-last-name">
          Last name <span className="text-destructive">*</span>
        </Label>
        <Input id="invite-last-name" required {...register("lastName")} />
        {errors.lastName && <p className="text-sm text-destructive">{errors.lastName.message}</p>}
      </div>
      <div className="flex flex-col gap-1.5 sm:col-span-2">
        <Label htmlFor="invite-department">
          Department <span className="text-destructive">*</span>
        </Label>
        <select
          id="invite-department"
          className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
          {...register("departmentId")}
          defaultValue=""
        >
          <option value="" disabled>
            Select a department
          </option>
          {departments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </select>
        {errors.departmentId && (
          <p className="text-sm text-destructive">{errors.departmentId.message}</p>
        )}
      </div>

      {formError && <p className="text-sm text-destructive sm:col-span-2">{formError}</p>}
      {success && <p className="text-sm text-success sm:col-span-2">{success}</p>}

      <div className="flex gap-2 sm:col-span-2">
        <Button type="submit" disabled={inviteMutation.isPending}>
          {inviteMutation.isPending ? "Sending…" : "Send invitation"}
        </Button>
        <Button type="button" variant="outline" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
