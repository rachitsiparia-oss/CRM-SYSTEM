"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AlertTriangle } from "lucide-react";

import { useCreateLead, useLeadDuplicates } from "@/lib/hooks/use-leads";
import { useDebouncedValue } from "@/lib/hooks/use-debounced-value";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { PhoneInput } from "@/components/forms/phone-input";
import { EmailInput } from "@/components/forms/email-input";
import { CurrencyInput } from "@/components/forms/currency-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const LEAD_TYPES = [
  "corporate_catering",
  "recurring_office_order",
  "event_booking",
  "group_dining",
  "partnership",
  "franchise_or_business_enquiry",
  "general_sales_enquiry",
];
const SOURCES = [
  "website",
  "phone",
  "walk_in",
  "whatsapp",
  "zomato_import",
  "swiggy_import",
  "meta_campaign",
  "google_campaign",
  "referral",
  "corporate_outreach",
  "event_enquiry",
  "offline_qr",
];
const PRIORITIES = ["low", "normal", "high", "urgent"];

const schema = z
  .object({
    leadType: z.string().min(1, "Select a lead type."),
    source: z.string().min(1, "Select a source."),
    priority: z.string().min(1),
    displayName: z.string().trim().min(1, "A lead name is required.").max(200),
    organizationName: z.string().trim().max(200).optional(),
    contactName: z.string().trim().max(160).optional(),
    phone: z.string().trim().optional(),
    email: z.string().trim().email("Enter a valid email address.").optional().or(z.literal("")),
    estimatedValueRupees: z.string().trim().optional(),
    partySize: z.string().trim().optional(),
    description: z.string().trim().optional(),
  })
  .refine((values) => !!(values.phone || values.email), {
    message: "A phone number or email address is required so the lead can be followed up.",
    path: ["phone"],
  });

type Values = z.infer<typeof schema>;

/** Rupees typed by a human → the integer minor units the API stores. The
 * backend is still the calculation authority (CLAUDE.md section 7); this is
 * only unit conversion at the input boundary. */
function toMinorUnits(rupees: string | undefined): number | null {
  if (!rupees) return null;
  const parsed = Number(rupees);
  if (!Number.isFinite(parsed) || parsed < 0) return null;
  return Math.round(parsed * 100);
}

export function LeadCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const createLead = useCreateLead();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { priority: "normal", leadType: "general_sales_enquiry", source: "website" },
  });

  const phone = useDebouncedValue(watch("phone") ?? "", 400);
  const email = useDebouncedValue(watch("email") ?? "", 400);
  const { data: duplicates } = useLeadDuplicates(phone, email);

  function resetForm() {
    reset({ priority: "normal", leadType: "general_sales_enquiry", source: "website" });
    setFormError(null);
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const created = await createLead.mutateAsync({
        lead_type: values.leadType,
        display_name: values.displayName,
        organization_name: values.organizationName || null,
        contact_name: values.contactName || null,
        phone_e164: values.phone || null,
        email: values.email || null,
        source: values.source,
        priority: values.priority,
        estimated_value_minor: toMinorUnits(values.estimatedValueRupees),
        party_size: values.partySize ? Number(values.partySize) : null,
        description: values.description || null,
      });
      resetForm();
      onOpenChange(false);
      router.push(`/leads/${created.data.id}`);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The lead could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New lead"
      size="lg"
      description="Capture the enquiry. Every new lead starts in the New status and moves through the pipeline from there."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="lead-create-form" disabled={createLead.isPending}>
            {createLead.isPending ? "Creating…" : "Create lead"}
          </Button>
        </>
      }
    >
      <form
        id="lead-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4 sm:grid-cols-2"
        noValidate
      >
        <FormField
          label="Lead name"
          htmlFor="lead-display-name"
          required
          error={errors.displayName?.message}
          className="sm:col-span-2"
        >
          <Input
            id="lead-display-name"
            placeholder="Who or what is this enquiry about?"
            {...register("displayName")}
          />
        </FormField>

        <FormField label="Lead type" htmlFor="lead-type" required error={errors.leadType?.message}>
          <Select
            value={watch("leadType")}
            onValueChange={(value) => setValue("leadType", value, { shouldDirty: true })}
          >
            <SelectTrigger id="lead-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LEAD_TYPES.map((option) => (
                <SelectItem key={option} value={option}>
                  {humanize(option)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Source" htmlFor="lead-source" required error={errors.source?.message}>
          <Select
            value={watch("source")}
            onValueChange={(value) => setValue("source", value, { shouldDirty: true })}
          >
            <SelectTrigger id="lead-source">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SOURCES.map((option) => (
                <SelectItem key={option} value={option}>
                  {humanize(option)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Organization" htmlFor="lead-organization">
          <Input id="lead-organization" {...register("organizationName")} />
        </FormField>

        <FormField label="Contact person" htmlFor="lead-contact">
          <Input id="lead-contact" {...register("contactName")} />
        </FormField>

        <FormField label="Phone" htmlFor="lead-phone" error={errors.phone?.message}>
          <PhoneInput id="lead-phone" {...register("phone")} />
        </FormField>

        <FormField label="Email" htmlFor="lead-email" error={errors.email?.message}>
          <EmailInput id="lead-email" {...register("email")} />
        </FormField>

        <FormField label="Priority" htmlFor="lead-priority" required>
          <Select
            value={watch("priority")}
            onValueChange={(value) => setValue("priority", value, { shouldDirty: true })}
          >
            <SelectTrigger id="lead-priority">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PRIORITIES.map((option) => (
                <SelectItem key={option} value={option}>
                  {humanize(option)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField
          label="Estimated value"
          htmlFor="lead-value"
          description="In rupees; stored as paise."
        >
          <CurrencyInput id="lead-value" {...register("estimatedValueRupees")} />
        </FormField>

        <FormField label="Party size" htmlFor="lead-party-size">
          <Input id="lead-party-size" type="number" min={1} {...register("partySize")} />
        </FormField>

        <FormField label="Description" htmlFor="lead-description" className="sm:col-span-2">
          <Textarea id="lead-description" rows={3} {...register("description")} />
        </FormField>

        {duplicates && duplicates.length > 0 && (
          <div
            role="status"
            className="border-warning/40 bg-warning/10 sm:col-span-2 flex flex-col gap-2 rounded-md border p-3"
          >
            <p className="flex items-center gap-2 text-sm font-medium">
              <AlertTriangle className="text-warning-foreground size-4" aria-hidden="true" />
              {duplicates.length === 1
                ? "An existing lead already uses this contact detail"
                : `${duplicates.length} existing leads already use this contact detail`}
            </p>
            <ul className="flex flex-col gap-1 text-sm">
              {duplicates.map((match) => (
                <li key={match.lead.id}>
                  <Link href={`/leads/${match.lead.id}`} className="font-medium hover:underline">
                    {match.lead.display_name}
                  </Link>
                  <span className="text-muted-foreground">
                    {" "}
                    · {match.lead.lead_number} · {humanize(match.lead.status)} ·{" "}
                    {match.match_reasons.map((reason) => humanize(reason)).join(", ")}
                  </span>
                </li>
              ))}
            </ul>
            <p className="text-muted-foreground text-xs">
              Open the existing lead if this is the same enquiry, rather than creating a second one.
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
