"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MapPin } from "lucide-react";

import {
  useAddCustomerAddress,
  useArchiveCustomerAddress,
  useCustomerAddresses,
} from "@/lib/hooks/use-customers";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { EmptyState } from "@/components/empty-state";
import { FormField } from "@/components/forms/form-field";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";

const schema = z.object({
  label: z.string().trim().max(64).optional(),
  addressLine1: z.string().trim().min(1, "Address line 1 is required.").max(200),
  addressLine2: z.string().trim().max(200).optional(),
  city: z.string().trim().min(1, "City is required.").max(100),
  state: z.string().trim().min(1, "State is required.").max(100),
  postalCode: z.string().trim().min(1, "Postal code is required.").max(16),
});

type Values = z.infer<typeof schema>;

export function CustomerAddresses({
  customerId,
  canEdit,
}: {
  customerId: string;
  canEdit: boolean;
}) {
  const { data: addresses, isLoading } = useCustomerAddresses(customerId);
  const addAddress = useAddCustomerAddress(customerId);
  const archiveAddress = useArchiveCustomerAddress(customerId);

  const [showForm, setShowForm] = useState(false);
  const [isDefault, setIsDefault] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [pendingArchiveId, setPendingArchiveId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await addAddress.mutateAsync({
        label: values.label || null,
        address_line1: values.addressLine1,
        address_line2: values.addressLine2 || null,
        city: values.city,
        state: values.state,
        postal_code: values.postalCode,
        is_default: isDefault,
      });
      reset();
      setIsDefault(false);
      setShowForm(false);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The address could not be saved.");
    }
  }

  return (
    <SectionCard
      title="Delivery addresses"
      description="Only one address can be the default at a time."
      actions={
        canEdit ? (
          <Button variant="outline" size="sm" onClick={() => setShowForm((open) => !open)}>
            {showForm ? "Cancel" : "Add address"}
          </Button>
        ) : null
      }
    >
      <div className="flex flex-col gap-4">
        {showForm && canEdit && (
          <form
            onSubmit={handleSubmit(onSubmit)}
            className="bg-muted/40 grid gap-4 rounded-md border p-4 sm:grid-cols-2"
            noValidate
          >
            <FormField label="Label" htmlFor="address-label" error={errors.label?.message}>
              <Input id="address-label" placeholder="Home, Office…" {...register("label")} />
            </FormField>
            <FormField
              label="Postal code"
              htmlFor="address-postal"
              required
              error={errors.postalCode?.message}
            >
              <Input id="address-postal" {...register("postalCode")} />
            </FormField>
            <FormField
              label="Address line 1"
              htmlFor="address-line1"
              required
              error={errors.addressLine1?.message}
              className="sm:col-span-2"
            >
              <Input id="address-line1" {...register("addressLine1")} />
            </FormField>
            <FormField
              label="Address line 2"
              htmlFor="address-line2"
              error={errors.addressLine2?.message}
              className="sm:col-span-2"
            >
              <Input id="address-line2" {...register("addressLine2")} />
            </FormField>
            <FormField label="City" htmlFor="address-city" required error={errors.city?.message}>
              <Input id="address-city" {...register("city")} />
            </FormField>
            <FormField label="State" htmlFor="address-state" required error={errors.state?.message}>
              <Input id="address-state" {...register("state")} />
            </FormField>

            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <Checkbox
                checked={isDefault}
                onCheckedChange={(checked) => setIsDefault(checked === true)}
              />
              Make this the default delivery address
            </label>

            {formError && (
              <p role="alert" className="text-destructive sm:col-span-2 text-sm">
                {formError}
              </p>
            )}

            <div className="sm:col-span-2">
              <Button type="submit" size="sm" disabled={addAddress.isPending}>
                {addAddress.isPending ? "Saving…" : "Save address"}
              </Button>
            </div>
          </form>
        )}

        {isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : !addresses || addresses.length === 0 ? (
          <EmptyState
            icon={MapPin}
            title="No addresses recorded"
            description="Add a delivery address so orders and reservations can reference it later."
          />
        ) : (
          <ul className="flex flex-col gap-3">
            {addresses.map((address) => (
              <li
                key={address.id}
                className="flex flex-wrap items-start justify-between gap-3 rounded-md border p-3"
              >
                <div className="text-sm">
                  <p className="flex items-center gap-2 font-medium">
                    {address.label ?? "Address"}
                    {address.is_default && <Badge variant="secondary">Default</Badge>}
                  </p>
                  <p className="text-muted-foreground">
                    {[
                      address.address_line1,
                      address.address_line2,
                      address.city,
                      address.state,
                      address.postal_code,
                      address.country,
                    ]
                      .filter(Boolean)
                      .join(", ")}
                  </p>
                </div>
                {canEdit && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setPendingArchiveId(address.id)}
                    disabled={archiveAddress.isPending}
                  >
                    Remove
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={pendingArchiveId !== null}
        onOpenChange={(open) => {
          if (!open) setPendingArchiveId(null);
        }}
        variant="delete"
        title="Remove this address?"
        description="The address is soft-deleted, so past orders that referenced it keep their history."
        confirmLabel="Remove address"
        onConfirm={async () => {
          if (!pendingArchiveId) return;
          try {
            await archiveAddress.mutateAsync(pendingArchiveId);
            setPendingArchiveId(null);
          } catch (error) {
            setFormError(
              error instanceof ApiError ? error.message : "The address could not be removed.",
            );
          }
        }}
      />
    </SectionCard>
  );
}
