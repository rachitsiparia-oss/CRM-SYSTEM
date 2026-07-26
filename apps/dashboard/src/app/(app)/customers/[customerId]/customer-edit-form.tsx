"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { Customer } from "@rkpr/contracts";

import { useUpdateCustomer } from "@/lib/hooks/use-customers";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { PhoneInput } from "@/components/forms/phone-input";
import { EmailInput } from "@/components/forms/email-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const DIETARY_OPTIONS = ["vegetarian", "non_vegetarian", "vegan", "jain", "no_preference"];
const SPICE_OPTIONS = ["mild", "medium", "spicy", "extra_spicy"];
const SEGMENT_OPTIONS = [
  "new",
  "repeat",
  "loyal",
  "vip",
  "at_risk",
  "dormant",
  "high_aov",
  "family",
  "corporate",
  "college_group",
  "delivery_first",
  "dine_in_first",
  "discount_sensitive",
  "complaint_recovery",
];
const UNSET = "__unset";

const schema = z.object({
  firstName: z.string().trim().max(100).optional(),
  lastName: z.string().trim().max(100).optional(),
  organizationName: z.string().trim().max(180).optional(),
  displayName: z.string().trim().min(1, "A display name is required.").max(200),
  primaryPhone: z.string().trim().optional(),
  primaryEmail: z
    .string()
    .trim()
    .email("Enter a valid email address.")
    .optional()
    .or(z.literal("")),
  preferredLanguage: z.string().trim().max(16).optional(),
  dietaryPreference: z.string(),
  spicePreference: z.string(),
  customerSegment: z.string(),
});

type Values = z.infer<typeof schema>;

function toNullable(value: string): string | null {
  return value === UNSET || value === "" ? null : value;
}

export function CustomerEditForm({ customer }: { customer: Customer }) {
  const [formError, setFormError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const updateCustomer = useUpdateCustomer(customer.id);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isDirty },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      firstName: customer.first_name ?? "",
      lastName: customer.last_name ?? "",
      organizationName: customer.organization_name ?? "",
      displayName: customer.display_name,
      primaryPhone: customer.primary_phone_e164 ?? "",
      primaryEmail: customer.primary_email ?? "",
      preferredLanguage: customer.preferred_language ?? "",
      dietaryPreference: customer.dietary_preference ?? UNSET,
      spicePreference: customer.spice_preference ?? UNSET,
      customerSegment: customer.customer_segment ?? UNSET,
    },
  });

  async function onSubmit(values: Values) {
    setFormError(null);
    setSaved(false);
    try {
      await updateCustomer.mutateAsync({
        first_name: values.firstName || null,
        last_name: values.lastName || null,
        organization_name: values.organizationName || null,
        display_name: values.displayName,
        primary_phone_e164: values.primaryPhone || null,
        primary_email: values.primaryEmail || null,
        preferred_language: values.preferredLanguage || null,
        dietary_preference: toNullable(values.dietaryPreference),
        spice_preference: toNullable(values.spicePreference),
        customer_segment: toNullable(values.customerSegment),
        // Optimistic concurrency: the backend returns 409 if this version is
        // stale, so a colleague's concurrent edit is never silently
        // overwritten (CLAUDE.md section 7).
        expected_version: customer.version,
      });
      setSaved(true);
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setFormError(
          "Someone else updated this customer while you were editing. Reload the page to see their changes, then re-apply yours.",
        );
        return;
      }
      setFormError(error instanceof ApiError ? error.message : "The changes could not be saved.");
    }
  }

  return (
    <SectionCard title="Edit profile" description="Identity, contact details, and preferences.">
      <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-3" noValidate>
        <FormField label="First name" htmlFor="edit-first-name" error={errors.firstName?.message}>
          <Input id="edit-first-name" {...register("firstName")} />
        </FormField>
        <FormField label="Last name" htmlFor="edit-last-name" error={errors.lastName?.message}>
          <Input id="edit-last-name" {...register("lastName")} />
        </FormField>
        <FormField
          label="Organization"
          htmlFor="edit-organization"
          error={errors.organizationName?.message}
        >
          <Input id="edit-organization" {...register("organizationName")} />
        </FormField>

        <FormField
          label="Display name"
          htmlFor="edit-display-name"
          required
          error={errors.displayName?.message}
        >
          <Input id="edit-display-name" {...register("displayName")} />
        </FormField>
        <FormField label="Phone" htmlFor="edit-phone" error={errors.primaryPhone?.message}>
          <PhoneInput id="edit-phone" {...register("primaryPhone")} />
        </FormField>
        <FormField label="Email" htmlFor="edit-email" error={errors.primaryEmail?.message}>
          <EmailInput id="edit-email" {...register("primaryEmail")} />
        </FormField>

        <FormField label="Preferred language" htmlFor="edit-language">
          <Input id="edit-language" placeholder="en, hi, kn…" {...register("preferredLanguage")} />
        </FormField>

        <FormField label="Dietary preference" htmlFor="edit-dietary">
          <Select
            value={watch("dietaryPreference")}
            onValueChange={(value) => setValue("dietaryPreference", value, { shouldDirty: true })}
          >
            <SelectTrigger id="edit-dietary">
              <SelectValue placeholder="Not recorded" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={UNSET}>Not recorded</SelectItem>
              {DIETARY_OPTIONS.map((option) => (
                <SelectItem key={option} value={option}>
                  {option.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Spice preference" htmlFor="edit-spice">
          <Select
            value={watch("spicePreference")}
            onValueChange={(value) => setValue("spicePreference", value, { shouldDirty: true })}
          >
            <SelectTrigger id="edit-spice">
              <SelectValue placeholder="Not recorded" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={UNSET}>Not recorded</SelectItem>
              {SPICE_OPTIONS.map((option) => (
                <SelectItem key={option} value={option}>
                  {option.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Segment" htmlFor="edit-segment" className="sm:col-span-3 sm:max-w-xs">
          <Select
            value={watch("customerSegment")}
            onValueChange={(value) => setValue("customerSegment", value, { shouldDirty: true })}
          >
            <SelectTrigger id="edit-segment">
              <SelectValue placeholder="Not set" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={UNSET}>Not set</SelectItem>
              {SEGMENT_OPTIONS.map((option) => (
                <SelectItem key={option} value={option}>
                  {option.replace(/_/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        {formError && (
          <p role="alert" className="text-destructive sm:col-span-3 text-sm">
            {formError}
          </p>
        )}
        {saved && !formError && <p className="text-success sm:col-span-3 text-sm">Changes saved.</p>}

        <div className="sm:col-span-3">
          <Button type="submit" disabled={updateCustomer.isPending || !isDirty}>
            {updateCustomer.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </SectionCard>
  );
}
