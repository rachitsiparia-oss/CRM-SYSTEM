"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { useCreateReservation, useDiningAreas } from "@/lib/hooks/use-reservations";
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

const NONE = "__none";

const schema = z.object({
  guestName: z.string().trim().min(1, "A guest name is required.").max(180),
  phoneE164: z.string().trim().optional(),
  partySize: z
    .string()
    .trim()
    .refine((v) => Number.isInteger(Number(v)) && Number(v) > 0, "Enter a valid party size."),
  reservationDate: z.string().min(1, "Select a date."),
  startTime: z.string().min(1, "Select a time."),
  diningAreaId: z.string().optional(),
  source: z.enum(["phone", "online", "whatsapp", "staff"]),
  specialRequests: z.string().trim().optional(),
});
type Values = z.infer<typeof schema>;

export function ReservationCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const { data: diningAreas } = useDiningAreas();
  const createReservation = useCreateReservation();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { partySize: "2", source: "phone" },
  });

  function resetForm() {
    reset({ partySize: "2", source: "phone" });
    setFormError(null);
  }

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const created = await createReservation.mutateAsync({
        guest_name: values.guestName,
        phone_e164: values.phoneE164 || null,
        party_size: Number(values.partySize),
        reservation_date: values.reservationDate,
        start_time: `${values.startTime}:00`,
        dining_area_id:
          values.diningAreaId && values.diningAreaId !== NONE ? values.diningAreaId : null,
        source: values.source,
        special_requests: values.specialRequests || null,
        idempotency_key: crypto.randomUUID(),
      });
      resetForm();
      onOpenChange(false);
      router.push(`/reservations/list/${created.data.id}`);
    } catch (error) {
      setFormError(
        error instanceof ApiError ? error.message : "The reservation could not be created.",
      );
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) resetForm();
        onOpenChange(next);
      }}
      title="New reservation"
      description="Create a reservation request — it still requires staff approval before confirmation."
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="reservation-create-form"
            disabled={createReservation.isPending}
          >
            {createReservation.isPending ? "Creating…" : "Create reservation"}
          </Button>
        </>
      }
    >
      <form
        id="reservation-create-form"
        onSubmit={handleSubmit(onSubmit)}
        className="grid gap-4 sm:grid-cols-2"
        noValidate
      >
        <FormField
          label="Guest name"
          htmlFor="reservation-guest-name"
          required
          error={errors.guestName?.message}
          className="sm:col-span-2"
        >
          <Input id="reservation-guest-name" {...register("guestName")} />
        </FormField>

        <FormField label="Phone" htmlFor="reservation-phone" error={errors.phoneE164?.message}>
          <Input id="reservation-phone" placeholder="98XXXXXXXX" {...register("phoneE164")} />
        </FormField>

        <FormField
          label="Party size"
          htmlFor="reservation-party-size"
          required
          error={errors.partySize?.message}
        >
          <Input
            id="reservation-party-size"
            inputMode="numeric"
            {...register("partySize")}
          />
        </FormField>

        <FormField
          label="Date"
          htmlFor="reservation-date"
          required
          error={errors.reservationDate?.message}
        >
          <Input id="reservation-date" type="date" {...register("reservationDate")} />
        </FormField>

        <FormField label="Time" htmlFor="reservation-time" required error={errors.startTime?.message}>
          <Input id="reservation-time" type="time" {...register("startTime")} />
        </FormField>

        <FormField label="Dining area" htmlFor="reservation-dining-area">
          <Select
            value={watch("diningAreaId") ?? NONE}
            onValueChange={(value) => setValue("diningAreaId", value)}
          >
            <SelectTrigger id="reservation-dining-area">
              <SelectValue placeholder="No preference" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>No preference</SelectItem>
              {(diningAreas ?? []).map((area) => (
                <SelectItem key={area.id} value={area.id}>
                  {area.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField label="Source" htmlFor="reservation-source" required>
          <Select
            value={watch("source")}
            onValueChange={(value) => setValue("source", value as Values["source"])}
          >
            <SelectTrigger id="reservation-source">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="phone">Phone</SelectItem>
              <SelectItem value="online">Online</SelectItem>
              <SelectItem value="whatsapp">WhatsApp</SelectItem>
              <SelectItem value="staff">Staff</SelectItem>
            </SelectContent>
          </Select>
        </FormField>

        <FormField
          label="Special requests"
          htmlFor="reservation-special-requests"
          className="sm:col-span-2"
        >
          <Textarea id="reservation-special-requests" {...register("specialRequests")} />
        </FormField>

        {formError && (
          <p role="alert" className="text-destructive sm:col-span-2 text-sm">
            {formError}
          </p>
        )}
      </form>
    </Modal>
  );
}
