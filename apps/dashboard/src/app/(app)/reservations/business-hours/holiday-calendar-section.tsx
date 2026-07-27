"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus } from "lucide-react";

import { useArchiveHoliday, useCreateHoliday, useHolidays } from "@/lib/hooks/use-reservations";
import { formatDate } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";

const schema = z.object({
  holidayDate: z.string().min(1, "Select a date."),
  name: z.string().trim().min(1, "A name is required.").max(120),
  isClosed: z.boolean(),
  opensAt: z.string().optional(),
  closesAt: z.string().optional(),
});
type Values = z.infer<typeof schema>;

export function HolidayCalendarSection({ canManage }: { canManage: boolean }) {
  const { data: holidays, isLoading } = useHolidays();
  const createHoliday = useCreateHoliday();
  const [showCreate, setShowCreate] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { isClosed: true } });

  const isClosed = watch("isClosed");

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await createHoliday.mutateAsync({
        holiday_date: values.holidayDate,
        name: values.name,
        is_closed: values.isClosed,
        opens_at: values.isClosed ? null : `${values.opensAt}:00`,
        closes_at: values.isClosed ? null : `${values.closesAt}:00`,
      });
      reset({ isClosed: true });
      setShowCreate(false);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "This holiday could not be added.");
    }
  }

  return (
    <SectionCard
      title="Holiday calendar"
      description="Full closures and special hours for specific dates."
      actions={
        canManage ? (
          <Button variant="outline" size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="size-3.5" />
            Add holiday
          </Button>
        ) : null
      }
    >
      {isLoading ? (
        <CardSkeleton />
      ) : !holidays || holidays.length === 0 ? (
        <EmptyState title="No holidays scheduled" description="Add a holiday to override the weekly hours for a specific date." />
      ) : (
        <ul className="flex flex-col gap-2">
          {holidays.map((holiday) => (
            <HolidayRow key={holiday.id} holiday={holiday} canManage={canManage} />
          ))}
        </ul>
      )}

      <Modal
        open={showCreate}
        onOpenChange={(next) => {
          if (!next) reset({ isClosed: true });
          setShowCreate(next);
        }}
        title="Add holiday"
        footer={
          <>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button type="submit" form="holiday-create-form" disabled={createHoliday.isPending}>
              {createHoliday.isPending ? "Adding…" : "Add"}
            </Button>
          </>
        }
      >
        <form
          id="holiday-create-form"
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4"
          noValidate
        >
          <FormField label="Date" htmlFor="holiday-date" required error={errors.holidayDate?.message}>
            <Input id="holiday-date" type="date" {...register("holidayDate")} />
          </FormField>
          <FormField label="Name" htmlFor="holiday-name" required error={errors.name?.message}>
            <Input id="holiday-name" placeholder="Diwali" {...register("name")} />
          </FormField>
          <label className="flex items-center gap-2 text-sm">
            <Checkbox
              checked={isClosed}
              onCheckedChange={(checked) => setValue("isClosed", checked === true)}
            />
            Fully closed
          </label>
          {!isClosed && (
            <div className="grid grid-cols-2 gap-4">
              <FormField label="Opens at" htmlFor="holiday-opens-at">
                <Input id="holiday-opens-at" type="time" {...register("opensAt")} />
              </FormField>
              <FormField label="Closes at" htmlFor="holiday-closes-at">
                <Input id="holiday-closes-at" type="time" {...register("closesAt")} />
              </FormField>
            </div>
          )}
          {formError && (
            <p role="alert" className="text-destructive text-sm">
              {formError}
            </p>
          )}
        </form>
      </Modal>
    </SectionCard>
  );
}

function HolidayRow({
  holiday,
  canManage,
}: {
  holiday: { id: string; holiday_date: string; name: string; is_closed: boolean };
  canManage: boolean;
}) {
  const archive = useArchiveHoliday(holiday.id);
  return (
    <li className="flex items-center justify-between rounded-md border p-3">
      <div>
        <p className="text-sm font-medium">{holiday.name}</p>
        <p className="text-muted-foreground text-xs">{formatDate(holiday.holiday_date)}</p>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge label={holiday.is_closed ? "Closed" : "Special hours"} tone={holiday.is_closed ? "danger" : "warning"} />
        {canManage && (
          <Button
            variant="outline"
            size="sm"
            disabled={archive.isPending}
            onClick={() => void archive.mutateAsync("Removed from holiday calendar.")}
          >
            Remove
          </Button>
        )}
      </div>
    </li>
  );
}
