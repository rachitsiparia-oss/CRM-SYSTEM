"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useCreateInventoryItem } from "@/lib/hooks/use-inventory-items";
import {
  useInventoryCategories,
  useInventoryLocations,
  useInventorySuppliers,
  useInventoryUnits,
} from "@/lib/hooks/use-inventory-reference";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { CurrencyInput } from "@/components/forms/currency-input";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const QUANTITY_PATTERN = /^\d+(\.\d{1,3})?$/;
const NONE = "__none";

const schema = z.object({
  name: z.string().trim().min(1, "A name is required.").max(180),
  categoryId: z.string().min(1, "Select a category."),
  baseUnitId: z.string().min(1, "Select a base unit."),
  defaultLocationId: z.string().optional(),
  preferredSupplierId: z.string().optional(),
  reorderLevel: z.string().trim().regex(QUANTITY_PATTERN, "Enter a valid quantity."),
  targetStock: z.string().trim().regex(QUANTITY_PATTERN, "Enter a valid quantity."),
  standardCostRupees: z
    .string()
    .trim()
    .optional()
    .refine((v) => !v || (Number.isFinite(Number(v)) && Number(v) >= 0), "Enter a valid cost."),
  isPerishable: z.boolean(),
  requiresBatchTracking: z.boolean(),
  requiresExpiryTracking: z.boolean(),
});
type Values = z.infer<typeof schema>;

export function InventoryItemCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const { data: categories } = useInventoryCategories();
  const { data: units } = useInventoryUnits();
  const { data: locations } = useInventoryLocations();
  const { data: suppliersPage } = useInventorySuppliers({ pageSize: 100 });
  const createItem = useCreateInventoryItem();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      reorderLevel: "0",
      targetStock: "0",
      isPerishable: false,
      requiresBatchTracking: false,
      requiresExpiryTracking: false,
    },
  });

  const requiresBatchTracking = watch("requiresBatchTracking");

  function resetForm() {
    reset({
      reorderLevel: "0",
      targetStock: "0",
      isPerishable: false,
      requiresBatchTracking: false,
      requiresExpiryTracking: false,
    });
    setFormError(null);
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const created = await createItem.mutateAsync({
        name: values.name,
        category_id: values.categoryId,
        base_unit_id: values.baseUnitId,
        default_location_id:
          values.defaultLocationId && values.defaultLocationId !== NONE
            ? values.defaultLocationId
            : null,
        preferred_supplier_id:
          values.preferredSupplierId && values.preferredSupplierId !== NONE
            ? values.preferredSupplierId
            : null,
        reorder_level: values.reorderLevel,
        target_stock: values.targetStock,
        standard_cost_minor: values.standardCostRupees
          ? Math.round(Number(values.standardCostRupees) * 100)
          : null,
        is_perishable: values.isPerishable,
        requires_batch_tracking: values.requiresBatchTracking,
        // An expiry-tracked item must also be batch-tracked — the same
        // invariant the database enforces (inventory_items' check
        // constraint), applied here so the API never rejects the form.
        requires_expiry_tracking: values.requiresBatchTracking && values.requiresExpiryTracking,
      });
      resetForm();
      onOpenChange(false);
      router.push(`/inventory/items/${created.data.id}`);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The item could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New inventory item"
      description="A stock-controlled ingredient or operational material — never a sellable menu product."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="inventory-item-create-form" disabled={createItem.isPending}>
            {createItem.isPending ? "Creating…" : "Create item"}
          </Button>
        </>
      }
    >
      <form
        id="inventory-item-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4 sm:grid-cols-2"
        noValidate
      >
        <FormField
          label="Name"
          htmlFor="item-name"
          required
          error={errors.name?.message}
          className="sm:col-span-2"
        >
          <Input id="item-name" {...register("name")} />
        </FormField>

        <FormField label="Category" htmlFor="item-category" required error={errors.categoryId?.message}>
          <Select
            value={watch("categoryId")}
            onValueChange={(value) => setValue("categoryId", value, { shouldDirty: true })}
          >
            <SelectTrigger id="item-category">
              <SelectValue placeholder="Select a category" />
            </SelectTrigger>
            <SelectContent>
              {(categories ?? []).map((category) => (
                <SelectItem key={category.id} value={category.id}>
                  {category.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Base unit" htmlFor="item-base-unit" required error={errors.baseUnitId?.message}>
          <Select
            value={watch("baseUnitId")}
            onValueChange={(value) => setValue("baseUnitId", value, { shouldDirty: true })}
          >
            <SelectTrigger id="item-base-unit">
              <SelectValue placeholder="Select a unit" />
            </SelectTrigger>
            <SelectContent>
              {(units ?? []).map((unit) => (
                <SelectItem key={unit.id} value={unit.id}>
                  {unit.name} ({unit.symbol})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Default location" htmlFor="item-location">
          <Select
            value={watch("defaultLocationId") ?? NONE}
            onValueChange={(value) => setValue("defaultLocationId", value)}
          >
            <SelectTrigger id="item-location">
              <SelectValue placeholder="No default location" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>No default location</SelectItem>
              {(locations ?? []).map((location) => (
                <SelectItem key={location.id} value={location.id}>
                  {location.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Preferred supplier" htmlFor="item-supplier">
          <Select
            value={watch("preferredSupplierId") ?? NONE}
            onValueChange={(value) => setValue("preferredSupplierId", value)}
          >
            <SelectTrigger id="item-supplier">
              <SelectValue placeholder="No preferred supplier" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>No preferred supplier</SelectItem>
              {(suppliersPage?.data ?? []).map((supplier) => (
                <SelectItem key={supplier.id} value={supplier.id}>
                  {supplier.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField
          label="Reorder level"
          htmlFor="item-reorder-level"
          error={errors.reorderLevel?.message}
        >
          <Input id="item-reorder-level" inputMode="decimal" {...register("reorderLevel")} />
        </FormField>

        <FormField label="Target stock" htmlFor="item-target-stock" error={errors.targetStock?.message}>
          <Input id="item-target-stock" inputMode="decimal" {...register("targetStock")} />
        </FormField>

        <FormField
          label="Standard cost (per base unit)"
          htmlFor="item-standard-cost"
          error={errors.standardCostRupees?.message}
        >
          <CurrencyInput id="item-standard-cost" {...register("standardCostRupees")} />
        </FormField>

        <div className="sm:col-span-2 flex flex-col gap-2">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={watch("isPerishable")}
              onCheckedChange={(checked) => setValue("isPerishable", checked === true)}
            />
            Perishable
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={requiresBatchTracking}
              onCheckedChange={(checked) => {
                const value = checked === true;
                setValue("requiresBatchTracking", value);
                if (!value) setValue("requiresExpiryTracking", false);
              }}
            />
            Requires batch tracking
          </label>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={watch("requiresExpiryTracking")}
              disabled={!requiresBatchTracking}
              onCheckedChange={(checked) => setValue("requiresExpiryTracking", checked === true)}
            />
            Requires expiry tracking
            {!requiresBatchTracking && (
              <span className="text-muted-foreground text-xs">(needs batch tracking)</span>
            )}
          </label>
        </div>

        {formError && (
          <p role="alert" className="text-destructive sm:col-span-2 text-sm">
            {formError}
          </p>
        )}
      </form>
    </Modal>
  );
}
