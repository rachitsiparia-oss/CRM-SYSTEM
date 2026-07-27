"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useCreateInventoryReceipt } from "@/lib/hooks/use-inventory-operations";
import { useInventoryLocations, useInventorySuppliers } from "@/lib/hooks/use-inventory-reference";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
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

const schema = z.object({
  supplierId: z.string().min(1, "Select a supplier."),
  storageLocationId: z.string().min(1, "Select a location."),
  receivedDate: z.string().min(1, "A received date is required."),
  supplierReference: z.string().trim().max(120).optional(),
  notes: z.string().trim().max(2000).optional(),
});
type Values = z.infer<typeof schema>;

export function ReceiptCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const { data: suppliersPage } = useInventorySuppliers({ pageSize: 100 });
  const { data: locations } = useInventoryLocations();
  const createReceipt = useCreateInventoryReceipt();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { receivedDate: new Date().toISOString().slice(0, 10) },
  });

  function resetForm() {
    reset({ receivedDate: new Date().toISOString().slice(0, 10) });
    setFormError(null);
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const created = await createReceipt.mutateAsync({
        supplier_id: values.supplierId,
        storage_location_id: values.storageLocationId,
        received_date: values.receivedDate,
        supplier_reference: values.supplierReference || null,
        notes: values.notes || null,
      });
      resetForm();
      onOpenChange(false);
      router.push(`/inventory/receipts/${created.data.id}`);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The receipt could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New goods receipt"
      description="Add line items after creating the draft. Posting updates stock and cost."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="receipt-create-form" disabled={createReceipt.isPending}>
            {createReceipt.isPending ? "Creating…" : "Create draft"}
          </Button>
        </>
      }
    >
      <form
        id="receipt-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4"
        noValidate
      >
        <FormField label="Supplier" htmlFor="receipt-supplier" required error={errors.supplierId?.message}>
          <Select
            value={watch("supplierId")}
            onValueChange={(value) => setValue("supplierId", value, { shouldDirty: true })}
          >
            <SelectTrigger id="receipt-supplier">
              <SelectValue placeholder="Select a supplier" />
            </SelectTrigger>
            <SelectContent>
              {(suppliersPage?.data ?? []).map((supplier) => (
                <SelectItem key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField
          label="Storage location"
          htmlFor="receipt-location"
          required
          error={errors.storageLocationId?.message}
        >
          <Select
            value={watch("storageLocationId")}
            onValueChange={(value) => setValue("storageLocationId", value, { shouldDirty: true })}
          >
            <SelectTrigger id="receipt-location">
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
          label="Received date"
          htmlFor="receipt-date"
          required
          error={errors.receivedDate?.message}
        >
          <Input id="receipt-date" type="date" {...register("receivedDate")} />
        </FormField>

        <FormField label="Supplier reference" htmlFor="receipt-ref">
          <Input id="receipt-ref" placeholder="Supplier invoice / DC number" {...register("supplierReference")} />
        </FormField>

        <FormField label="Notes" htmlFor="receipt-notes">
          <Textarea id="receipt-notes" rows={2} {...register("notes")} />
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
