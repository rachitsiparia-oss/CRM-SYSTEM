"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { CurrentUser, DataResponse } from "@rkpr/contracts";

import { apiFetchClient } from "@/lib/api/browser";
import { currentUserQueryKey } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PhoneInput } from "@/components/forms/phone-input";

const profileSchema = z.object({
  phone_e164: z.string().optional().or(z.literal("")),
  timezone: z.string().min(1, "Timezone is required"),
  preferred_language: z.string().optional().or(z.literal("")),
});
type ProfileValues = z.infer<typeof profileSchema>;

export function ProfileForm({ user }: { user: CurrentUser }) {
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      phone_e164: user.phone_e164 ?? "",
      timezone: user.timezone,
      preferred_language: user.preferred_language ?? "",
    },
  });

  const mutation = useMutation({
    mutationFn: (values: ProfileValues) =>
      apiFetchClient<DataResponse<CurrentUser>>("/api/v1/auth/me", {
        method: "PATCH",
        body: {
          phone_e164: values.phone_e164 || null,
          timezone: values.timezone,
          preferred_language: values.preferred_language || null,
        },
      }),
    onSuccess: (response) => {
      queryClient.setQueryData(currentUserQueryKey, response);
      setSuccess(true);
      setFormError(null);
    },
    onError: (error: unknown) => {
      setFormError(error instanceof ApiError ? error.message : "Could not update your profile.");
      setSuccess(false);
    },
  });

  return (
    <form
      onSubmit={handleSubmit((values) => mutation.mutate(values))}
      className="flex max-w-md flex-col gap-4"
      noValidate
    >
      <div className="flex flex-col gap-1.5">
        <Label>Display name</Label>
        <Input value={user.display_name} disabled readOnly />
        <p className="text-muted-foreground text-xs">
          Contact an administrator to change your name.
        </p>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label>Email</Label>
        <Input value={user.email} disabled readOnly />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="phone_e164">Phone</Label>
        <PhoneInput id="phone_e164" disabled={mutation.isPending} {...register("phone_e164")} />
        {errors.phone_e164 && (
          <p className="text-destructive text-sm">{errors.phone_e164.message}</p>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="timezone">Timezone</Label>
        <Input id="timezone" disabled={mutation.isPending} {...register("timezone")} />
        {errors.timezone && <p className="text-destructive text-sm">{errors.timezone.message}</p>}
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="preferred_language">Preferred language</Label>
        <Input
          id="preferred_language"
          placeholder="en"
          disabled={mutation.isPending}
          {...register("preferred_language")}
        />
      </div>

      {formError && (
        <p role="alert" className="text-destructive text-sm">
          {formError}
        </p>
      )}
      {success && !isDirty && <p className="text-sm text-success">Profile updated.</p>}

      <Button type="submit" disabled={mutation.isPending} className="w-fit">
        {mutation.isPending ? "Saving…" : "Save changes"}
      </Button>
    </form>
  );
}
