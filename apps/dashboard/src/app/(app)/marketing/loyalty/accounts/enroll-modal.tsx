"use client";

import { useMemo, useState } from "react";

import { useEnrollLoyalty, useLoyaltyPrograms } from "@/lib/hooks/use-loyalty";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function EnrollModal({
  customerId,
  open,
  onOpenChange,
}: {
  customerId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: programs } = useLoyaltyPrograms();
  const enroll = useEnrollLoyalty();

  const activePrograms = useMemo(
    () => (programs ?? []).filter((p) => p.status === "active"),
    [programs],
  );
  const defaultProgramId = useMemo(
    () => activePrograms.find((p) => p.is_default)?.id ?? activePrograms[0]?.id ?? "",
    [activePrograms],
  );

  const [programId, setProgramId] = useState(defaultProgramId);
  const [error, setError] = useState<string | null>(null);

  const effectiveProgramId = programId || defaultProgramId;

  function reset() {
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Enroll in loyalty program"
      description="Creates a new points account for this customer."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!effectiveProgramId || enroll.isPending}
            onClick={() => {
              setError(null);
              enroll.mutate(
                { customer_id: customerId, program_id: effectiveProgramId, enrollment_source: "staff" },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not enroll this customer."),
                },
              );
            }}
          >
            Enroll
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {activePrograms.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No active loyalty programs. Activate a program before enrolling members.
          </p>
        ) : (
          <div className="flex flex-col gap-1.5">
            <Label>Program</Label>
            <Select value={effectiveProgramId} onValueChange={setProgramId}>
              <SelectTrigger>
                <SelectValue placeholder="Select a program" />
              </SelectTrigger>
              <SelectContent>
                {activePrograms.map((program) => (
                  <SelectItem key={program.id} value={program.id}>
                    {program.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>
    </Modal>
  );
}
