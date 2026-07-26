"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertTriangle } from "lucide-react";

import { useCreateCustomer, useCustomerDuplicates } from "@/lib/hooks/use-customers";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
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

const schema = z
  .object({
    customerType: z.enum(["individual", "corporate"]),
    firstName: z.string().trim().max(100).optional(),
    lastName: z.string().trim().max(100).optional(),
    organizationName: z.string().trim().max(180).optional(),
    primaryPhone: z.string().trim().optional(),
    primaryEmail: z.string().trim().email("Enter a valid email address.").optional().or(z.literal("")),
  })
  // The backend derives display_name from these and rejects a record with
  // none of them (app/customers/service.py::derive_display_name); mirroring
  // the rule here turns a 400 into inline guidance.
  .refine(
    (values) =>
      values.customerType === "corporate"
        ? !!values.organizationName
        : !!(values.firstName || values.lastName),
    {
      message: "Provide a first or last name (or an organization name for a corporate customer).",
      path: ["firstName"],
    },
  )
  .refine((values) => !!(values.primaryPhone || values.primaryEmail), {
    message: "A phone number or email address is required so duplicates can be detected.",
    path: ["primaryPhone"],
  });

type Values = z.infer<typeof schema>;

export function CustomerCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const createCustomer = useCreateCustomer();

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setValue,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { customerType: "individual" },
  });

  const customerType = watch("customerType");
  const phone = useDebouncedValue(watch("primaryPhone") ?? "", 400);
  const email = useDebouncedValue(watch("primaryEmail") ?? "", 400);

  // Duplicate detection runs while staff type, before anything is saved —
  // CORE_CRM_MODULES.md section 4.7. A match is a warning, never a block:
  // two guests can legitimately share a landline.
  const { data: duplicates } = useCustomerDuplicates(phone, email);

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const created = await createCustomer.mutateAsync({
        customer_type: values.customerType,
        first_name: values.firstName || null,
        last_name: values.lastName || null,
        organization_name: values.organizationName || null,
        primary_phone_e164: values.primaryPhone || null,
        primary_email: values.primaryEmail || null,
      });
      reset({ customerType: "individual" });
      onOpenChange(false);
      router.push(`/customers/${created.data.id}`);
    } catch (error) {
      setFormError(
        error instanceof ApiError ? error.message : "The customer could not be created.",
      );
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          reset({ customerType: "individual" });
          setFormError(null);
        }
        onOpenChange(next);
      }}
      title="New customer"
      description="Identity and contact details. Order history and lifetime value fill in automatically once the customer orders."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="customer-create-form" disabled={createCustomer.isPending}>
            {createCustomer.isPending ? "Creating…" : "Create customer"}
          </Button>
        </>
      }
    >
      <form
        id="customer-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4 sm:grid-cols-2"
        noValidate
      >
        <FormField label="Customer type" htmlFor="customer-type" required className="sm:col-span-2">
          <Select
            value={customerType}
            onValueChange={(value) => setValue("customerType", value as Values["customerType"])}
          >
            <SelectTrigger id="customer-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="individual">Individual</SelectItem>
              <SelectItem value="corporate">Corporate</SelectItem>
            </SelectContent>
          </Select>
        </FormField>

        {customerType === "corporate" ? (
          <FormField
            label="Organization name"
            htmlFor="organization-name"
            required
            error={errors.organizationName?.message ?? errors.firstName?.message}
            className="sm:col-span-2"
          >
            <Input id="organization-name" {...register("organizationName")} />
          </FormField>
        ) : (
          <>
            <FormField label="First name" htmlFor="first-name" error={errors.firstName?.message}>
              <Input id="first-name" {...register("firstName")} />
            </FormField>
            <FormField label="Last name" htmlFor="last-name" error={errors.lastName?.message}>
              <Input id="last-name" {...register("lastName")} />
            </FormField>
          </>
        )}

        <FormField
          label="Phone"
          htmlFor="primary-phone"
          error={errors.primaryPhone?.message}
          description="Indian mobile number; normalized to E.164 on save."
        >
          <PhoneInput id="primary-phone" {...register("primaryPhone")} />
        </FormField>

        <FormField label="Email" htmlFor="primary-email" error={errors.primaryEmail?.message}>
          <EmailInput id="primary-email" {...register("primaryEmail")} />
        </FormField>

        {duplicates && duplicates.length > 0 && (
          <div
            role="status"
            className="border-warning/40 bg-warning/10 sm:col-span-2 flex flex-col gap-2 rounded-md border p-3"
          >
            <p className="flex items-center gap-2 text-sm font-medium">
              <AlertTriangle className="text-warning-foreground size-4" aria-hidden="true" />
              {duplicates.length === 1
                ? "An existing customer already uses this contact detail"
                : `${duplicates.length} existing customers already use this contact detail`}
            </p>
            <ul className="flex flex-col gap-1 text-sm">
              {duplicates.map((match) => (
                <li key={match.customer.id}>
                  <Link
                    href={`/customers/${match.customer.id}`}
                    className="font-medium hover:underline"
                  >
                    {match.customer.display_name}
                  </Link>
                  <span className="text-muted-foreground">
                    {" "}
                    · {match.customer.customer_number} ·{" "}
                    {match.match_reasons.map((reason) => humanize(reason)).join(", ")}
                  </span>
                </li>
              ))}
            </ul>
            <p className="text-muted-foreground text-xs">
              You can still create this customer — open the existing record first if it is the same
              person, and merge them afterwards if a duplicate is created.
            </p>
          </div>
        )}

        {formError && (
          <p role="alert" className="text-destructive sm:col-span-2 text-sm">
            {formError}
          </p>
        )}
      </form>
    </Modal>
  );
}
