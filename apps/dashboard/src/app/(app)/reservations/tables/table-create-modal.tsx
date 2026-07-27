"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useCreateTable, useDiningAreas } from "@/lib/hooks/use-reservations";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
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

const schema = z.object({
  diningAreaId: z.string().min(1, "Select a dining area."),
  tableNumber: z.string().trim().min(1, "A table number is required.").max(20),
  capacity: z.string().trim().refine((v) => Number.isInteger(Number(v)) && Number(v) > 0, "Enter a valid capacity."),
  shape: z.enum(["round", "square", "rectangle", "oval", "booth", "bar", "custom"]),
  isWheelchairAccessible: z.boolean(),
});
type Values = z.infer<typeof schema>;

export function TableCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [formError, setFormError] = useState<string | null>(null);
  const { data: diningAreas } = useDiningAreas();
  const createTable = useCreateTable();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { capacity: "4", shape: "square", isWheelchairAccessible: false },
  });

  function resetForm() {
    reset({ capacity: "4", shape: "square", isWheelchairAccessible: false });
    setFormError(null);
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await createTable.mutateAsync({
        dining_area_id: values.diningAreaId,
        table_number: values.tableNumber,
        capacity: Number(values.capacity),
        shape: values.shape,
        is_wheelchair_accessible: values.isWheelchairAccessible,
      });
      resetForm();
      onOpenChange(false);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "The table could not be created.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New table"
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" form="table-create-form" disabled={createTable.isPending}>
            {createTable.isPending ? "Creating…" : "Create table"}
          </Button>
        </>
      }
    >
      <form
        id="table-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4 sm:grid-cols-2"
        noValidate
      >
        <FormField
          label="Dining area"
          htmlFor="table-dining-area"
          required
          error={errors.diningAreaId?.message}
          className="sm:col-span-2"
        >
          <Select
            value={watch("diningAreaId")}
            onValueChange={(value) => setValue("diningAreaId", value, { shouldDirty: true })}
          >
            <SelectTrigger id="table-dining-area">
              <SelectValue placeholder="Select a dining area" />
            </SelectTrigger>
            <SelectContent>
              {(diningAreas ?? []).map((area) => (
                <SelectItem key={area.id} value={area.id}>
                  {area.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Table number" htmlFor="table-number" required error={errors.tableNumber?.message}>
          <Input id="table-number" {...register("tableNumber")} />
        </FormField>

        <FormField label="Capacity" htmlFor="table-capacity" required error={errors.capacity?.message}>
          <Input id="table-capacity" inputMode="numeric" {...register("capacity")} />
        </FormField>

        <FormField label="Shape" htmlFor="table-shape">
          <Select
            value={watch("shape")}
            onValueChange={(value) => setValue("shape", value as Values["shape"])}
          >
            <SelectTrigger id="table-shape">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["round", "square", "rectangle", "oval", "booth", "bar", "custom"].map((shape) => (
                <SelectItem key={shape} value={shape}>
                  {shape[0]!.toUpperCase() + shape.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <div className="flex items-center sm:col-span-2">
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={watch("isWheelchairAccessible")}
              onCheckedChange={(checked) => setValue("isWheelchairAccessible", checked === true)}
            />
            Wheelchair accessible
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
