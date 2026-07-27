"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useCreateInventoryTransfer } from "@/lib/hooks/use-inventory-operations";
import { useInventoryLocations } from "@/lib/hooks/use-inventory-reference";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const schema = z
  .object({
    sourceLocationId: z.string().min(1, "Select a source location."),
    destinationLocationId: z.string().min(1, "Select a destination location."),
    notes: z.string().trim().max(2000).optional(),
  })
  .refine((v) => v.sourceLocationId !== v.destinationLocationId, {
    message: "Source and destination must be different.",
    path: ["destinationLocationId"],
  });
type Values = z.infer<typeof schema>;

export function TransferCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const { data: locations } = useInventoryLocations();
  const createTransfer = useCreateInventoryTransfer();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  function resetForm() {
    reset();
    setFormError(null);
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const created = await createTransfer.mutateAsync({
        source_location_id: values.sourceLocationId,
        destination_location_id: values.destinationLocationId,
        notes: values.notes || null,
      });
      resetForm();
      onOpenChange(false);
      router.push(`/inventory/transfers/${created.data.id}`);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The transfer could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New stock transfer"
      description="Add line items after creating the draft. Posting moves stock atomically."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="transfer-create-form" disabled={createTransfer.isPending}>
            {createTransfer.isPending ? "Creating…" : "Create draft"}
          </Button>
        </>
      }
    >
      <form
        id="transfer-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4"
        noValidate
      >
        <FormField
          label="Source location"
          htmlFor="transfer-source"
          required
          error={errors.sourceLocationId?.message}
        >
          <Select
            value={watch("sourceLocationId")}
            onValueChange={(value) => setValue("sourceLocationId", value, { shouldDirty: true })}
          >
            <SelectTrigger id="transfer-source">
              <SelectValue placeholder="Select a location" />
            </SelectTrigger>
            <SelectContent>
              {(locations ?? []).map((location) => (
                <SelectItem key={location.id} value={location.id}>
                  {location.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField
          label="Destination location"
          htmlFor="transfer-destination"
          required
          error={errors.destinationLocationId?.message}
        >
          <Select
            value={watch("destinationLocationId")}
            onValueChange={(value) =>
              setValue("destinationLocationId", value, { shouldDirty: true })
            }
          >
            <SelectTrigger id="transfer-destination">
              <SelectValue placeholder="Select a location" />
            </SelectTrigger>
            <SelectContent>
              {(locations ?? []).map((location) => (
                <SelectItem key={location.id} value={location.id}>
                  {location.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Notes" htmlFor="transfer-notes">
          <Textarea id="transfer-notes" rows={2} {...register("notes")} />
        </FormField>

        {formError && (
          <p role="alert" className="text-destructive text-sm">
            {formError}
          </p>
        )}
      </form>
    </Modal>
  );
}
