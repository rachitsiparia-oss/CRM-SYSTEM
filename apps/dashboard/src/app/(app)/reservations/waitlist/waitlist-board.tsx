"use client";

import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus } from "lucide-react";

import {
  useAddToWaitlist,
  useCancelWaitlistEntry,
  useCreateWalkIn,
  useDiningAreas,
  useNotifyWaitlistEntry,
  usePromoteWaitlistEntry,
  useWaitlist,
} from "@/lib/hooks/use-reservations";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { WAITLIST_STATUS_TONES, formatDateTime, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  diningAreaId: z.string().optional(),
  estimatedWaitMinutes: z.string().trim().optional(),
});
type Values = z.infer<typeof schema>;

export function WaitlistBoard() {
  const { data: currentUser } = useCurrentUser();
  const { data, isLoading } = useWaitlist("waiting");
  const { data: diningAreas } = useDiningAreas();
  const [showCreate, setShowCreate] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [seatingError, setSeatingError] = useState<Record<string, string>>({});

  const addToWaitlist = useAddToWaitlist();
  const notifyEntry = useNotifyWaitlistEntry();
  const cancelEntry = useCancelWaitlistEntry();
  const promoteEntry = usePromoteWaitlistEntry();
  const createWalkIn = useCreateWalkIn();

  const canManage = hasPermission(currentUser, "reservations.waitlist.manage");
  const diningAreaName = useMemo(
    () => new Map((diningAreas ?? []).map((a) => [a.id, a.name])),
    [diningAreas],
  );

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { partySize: "2" } });

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      await addToWaitlist.mutateAsync({
        guest_name: values.guestName,
        phone_e164: values.phoneE164 || null,
        party_size: Number(values.partySize),
        dining_area_id: values.diningAreaId && values.diningAreaId !== NONE ? values.diningAreaId : null,
        estimated_wait_minutes: values.estimatedWaitMinutes
          ? Number(values.estimatedWaitMinutes)
          : null,
      });
      reset({ partySize: "2" });
      setShowCreate(false);
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : "This guest could not be added.");
    }
  }

  async function seatNow(entry: {
    id: string;
    guest_name: string;
    phone_e164: string | null;
    party_size: number;
    dining_area_id: string | null;
  }) {
    setSeatingError((prev) => ({ ...prev, [entry.id]: "" }));
    try {
      const reservation = await createWalkIn.mutateAsync({
        guest_name: entry.guest_name,
        phone_e164: entry.phone_e164,
        party_size: entry.party_size,
        dining_area_id: entry.dining_area_id,
      });
      await promoteEntry.mutateAsync({ entryId: entry.id, reservationId: reservation.data.id });
    } catch (error) {
      setSeatingError((prev) => ({
        ...prev,
        [entry.id]: error instanceof ApiError ? error.message : "This guest could not be seated.",
      }));
    }
  }

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Waitlist"
        description="Guests waiting for a table right now, in priority order."
        actions={
          canManage ? (
            <Button onClick={() => setShowCreate(true)}>
              <Plus className="size-4" />
              Add to waitlist
            </Button>
          ) : null
        }
      />

      <SectionCard title="Waiting">
        {isLoading ? (
          <CardSkeleton />
        ) : !data || data.data.length === 0 ? (
          <EmptyState title="No one is waiting" description="Guests added to the waitlist will appear here." />
        ) : (
          <ul className="flex flex-col gap-2">
            {data.data.map((entry) => (
              <li key={entry.id} className="flex flex-col gap-2 rounded-md border p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{entry.guest_name}</p>
                    <p className="text-muted-foreground text-xs">
                      Party of {entry.party_size}
                      {entry.dining_area_id ? ` · ${diningAreaName.get(entry.dining_area_id)}` : ""} ·{" "}
                      {formatDateTime(entry.requested_at)}
                      {entry.estimated_wait_minutes ? ` · ~${entry.estimated_wait_minutes} min` : ""}
                    </p>
                  </div>
                  <StatusBadge label={humanize(entry.status)} tone={WAITLIST_STATUS_TONES[entry.status]} />
                </div>
                {canManage && (
                  <div className="flex flex-wrap gap-2">
                    {entry.status === "waiting" && (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={notifyEntry.isPending}
                        onClick={() => void notifyEntry.mutateAsync(entry.id)}
                      >
                        Notify
                      </Button>
                    )}
                    <Button
                      size="sm"
                      disabled={createWalkIn.isPending || promoteEntry.isPending}
                      onClick={() => void seatNow(entry)}
                    >
                      Seat now
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      disabled={cancelEntry.isPending}
                      onClick={() => void cancelEntry.mutateAsync({ entryId: entry.id })}
                    >
                      Cancel
                    </Button>
                  </div>
                )}
                {seatingError[entry.id] && (
                  <p role="alert" className="text-destructive text-xs">
                    {seatingError[entry.id]}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </SectionCard>

      <Modal
        open={showCreate}
        onOpenChange={(next) => {
          if (!next) reset({ partySize: "2" });
          setShowCreate(next);
        }}
        title="Add to waitlist"
        footer={
          <>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button type="submit" form="waitlist-create-form" disabled={addToWaitlist.isPending}>
              {addToWaitlist.isPending ? "Adding…" : "Add"}
            </Button>
          </>
        }
      >
        <form
          id="waitlist-create-form"
          onSubmit={handleSubmit(onSubmit)}
          className="flex flex-col gap-4"
          noValidate
        >
          <FormField label="Guest name" htmlFor="waitlist-guest-name" required error={errors.guestName?.message}>
            <Input id="waitlist-guest-name" {...register("guestName")} />
          </FormField>
          <FormField label="Phone" htmlFor="waitlist-phone">
            <Input id="waitlist-phone" placeholder="98XXXXXXXX" {...register("phoneE164")} />
          </FormField>
          <FormField label="Party size" htmlFor="waitlist-party-size" required error={errors.partySize?.message}>
            <Input id="waitlist-party-size" inputMode="numeric" {...register("partySize")} />
          </FormField>
          <FormField label="Dining area preference" htmlFor="waitlist-dining-area">
            <Select
              value={watch("diningAreaId") ?? NONE}
              onValueChange={(value) => setValue("diningAreaId", value)}
            >
              <SelectTrigger id="waitlist-dining-area">
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
          <FormField label="Estimated wait (minutes)" htmlFor="waitlist-estimated-wait">
            <Input id="waitlist-estimated-wait" inputMode="numeric" {...register("estimatedWaitMinutes")} />
          </FormField>
          {formError && (
            <p role="alert" className="text-destructive text-sm">
              {formError}
            </p>
          )}
        </form>
      </Modal>
    </div>
  );
}
