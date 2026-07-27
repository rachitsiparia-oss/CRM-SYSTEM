"use client";

import { useState } from "react";
import type { Reservation } from "@rkpr/contracts";

import {
  useAssignReservationTables,
  useAvailability,
  useUnassignReservationTables,
} from "@/lib/hooks/use-reservations";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const ASSIGNABLE_STATUSES = new Set([
  "approved",
  "confirmation_sending",
  "confirmed",
  "reminder_scheduled",
  "arrived",
  "seated",
]);

export function ReservationAssignControl({ reservation }: { reservation: Reservation }) {
  const [selectedTableId, setSelectedTableId] = useState<string>("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: availableTables, isLoading } = useAvailability({
    targetDate: reservation.reservation_date,
    startTime: reservation.start_time,
    endTime: reservation.end_time ?? undefined,
    partySize: reservation.party_size,
    diningAreaId: reservation.dining_area_id ?? undefined,
  });

  const assign = useAssignReservationTables(reservation.id);
  const unassign = useUnassignReservationTables(reservation.id);

  if (!ASSIGNABLE_STATUSES.has(reservation.status)) return null;

  async function handleAssign() {
    setError(null);
    setResult(null);
    if (!selectedTableId) return;
    try {
      const assignments = await assign.mutateAsync([selectedTableId]);
      setResult(`Assigned to ${assignments.data.length} table(s).`);
      setSelectedTableId("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The table could not be assigned.");
    }
  }

  async function handleUnassign() {
    setError(null);
    setResult(null);
    try {
      await unassign.mutateAsync(true);
      setResult("Tables released.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The table could not be unassigned.");
    }
  }

  return (
    <SectionCard
      title="Table assignment"
      description="Only tables with no conflict for this reservation's date, time, and party size are offered."
    >
      <div className="flex flex-wrap items-end gap-3">
        <FormField label="Available table" htmlFor="reservation-assign-table" className="min-w-56">
          <Select value={selectedTableId} onValueChange={setSelectedTableId}>
            <SelectTrigger id="reservation-assign-table">
              <SelectValue placeholder={isLoading ? "Loading…" : "Select a table"} />
            </SelectTrigger>
            <SelectContent>
              {(availableTables ?? []).map((table) => (
                <SelectItem key={table.id} value={table.id}>
                  {table.table_number} (seats {table.capacity})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <Button disabled={!selectedTableId || assign.isPending} onClick={() => void handleAssign()}>
          {assign.isPending ? "Assigning…" : "Assign table"}
        </Button>
        <Button variant="outline" disabled={unassign.isPending} onClick={() => void handleUnassign()}>
          {unassign.isPending ? "Releasing…" : "Unassign tables"}
        </Button>
      </div>

      {result && <p className="text-muted-foreground mt-3 text-sm">{result}</p>}
      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}
    </SectionCard>
  );
}
