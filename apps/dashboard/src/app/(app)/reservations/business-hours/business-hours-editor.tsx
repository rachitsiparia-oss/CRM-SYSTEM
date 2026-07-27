"use client";

import { useState } from "react";
import type { BusinessHours } from "@rkpr/contracts";

import { useBusinessHours, useUpdateBusinessHours } from "@/lib/hooks/use-reservations";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { SectionCard } from "@/components/section-card";
import { CardSkeleton } from "@/components/skeletons/card-skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { HolidayCalendarSection } from "./holiday-calendar-section";

// PROJECT_PLAN.md section 3.3 / app.reservations.models.business_hours:
// day_of_week follows date.weekday() — 0 is Monday.
const DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function BusinessHoursRow({ hours, canManage }: { hours: BusinessHours; canManage: boolean }) {
  const update = useUpdateBusinessHours(hours.day_of_week);
  const [isClosed, setIsClosed] = useState(hours.is_closed);
  const [opensAt, setOpensAt] = useState(hours.opens_at ?? "");
  const [closesAt, setClosesAt] = useState(hours.closes_at ?? "");
  const [closesNextDay, setClosesNextDay] = useState(hours.closes_next_day);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setError(null);
    try {
      await update.mutateAsync({
        is_closed: isClosed,
        opens_at: isClosed ? null : opensAt || null,
        closes_at: isClosed ? null : closesAt || null,
        closes_next_day: isClosed ? false : closesNextDay,
        expected_version: hours.version,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "These hours could not be saved.");
    }
  }

  return (
    <div className="flex flex-col gap-2 rounded-md border p-3 sm:flex-row sm:items-center sm:justify-between">
      <span className="w-24 text-sm font-medium">{DAY_NAMES[hours.day_of_week]}</span>
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={isClosed}
            disabled={!canManage}
            onCheckedChange={(checked) => setIsClosed(checked === true)}
          />
          Closed
        </label>
        {!isClosed && (
          <>
            <Input
              type="time"
              className="w-32"
              value={opensAt.slice(0, 5)}
              disabled={!canManage}
              onChange={(e) => setOpensAt(`${e.target.value}:00`)}
            />
            <span className="text-muted-foreground text-sm">to</span>
            <Input
              type="time"
              className="w-32"
              value={closesAt.slice(0, 5)}
              disabled={!canManage}
              onChange={(e) => setClosesAt(`${e.target.value}:00`)}
            />
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={closesNextDay}
                disabled={!canManage}
                onCheckedChange={(checked) => setClosesNextDay(checked === true)}
              />
              Closes after midnight
            </label>
          </>
        )}
        {canManage && (
          <Button size="sm" variant="outline" disabled={update.isPending} onClick={() => void save()}>
            {update.isPending ? "Saving…" : "Save"}
          </Button>
        )}
      </div>
      {error && (
        <p role="alert" className="text-destructive text-xs">
          {error}
        </p>
      )}
    </div>
  );
}

export function BusinessHoursEditor() {
  const { data: currentUser } = useCurrentUser();
  const { data: hours, isLoading } = useBusinessHours();
  const canManage = hasPermission(currentUser, "reservations.settings.manage");

  return (
    <div className="flex flex-1 flex-col gap-4 p-6">
      <PageHeader
        title="Business Hours"
        description="Weekly opening hours and holiday overrides — used by the availability engine to accept or reject bookings."
      />

      <SectionCard title="Weekly hours">
        {isLoading ? (
          <CardSkeleton />
        ) : (
          <div className="flex flex-col gap-2">
            {(hours ?? [])
              .slice()
              .sort((a, b) => a.day_of_week - b.day_of_week)
              .map((day) => (
                <BusinessHoursRow key={day.id} hours={day} canManage={canManage} />
              ))}
          </div>
        )}
      </SectionCard>

      <HolidayCalendarSection canManage={canManage} />
    </div>
  );
}
