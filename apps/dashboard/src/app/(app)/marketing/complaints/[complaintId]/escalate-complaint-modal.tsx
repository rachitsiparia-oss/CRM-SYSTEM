"use client";

import { useState } from "react";

import { useEscalateComplaint } from "@/lib/hooks/use-complaints";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

export function EscalateComplaintModal({
  complaintId,
  open,
  onOpenChange,
}: {
  complaintId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const escalateComplaint = useEscalateComplaint(complaintId);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setReason("");
          setError(null);
        }
        onOpenChange(next);
      }}
      title="Escalate complaint"
      description="Manually escalate this complaint to the next level."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!reason.trim() || escalateComplaint.isPending}
            onClick={() => {
              setError(null);
              escalateComplaint.mutate(
                { reason: reason.trim() },
                {
                  onSuccess: () => {
                    setReason("");
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not escalate."),
                },
              );
            }}
          >
            {escalateComplaint.isPending ? "Escalating…" : "Escalate"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="escalate-reason">Reason</Label>
          <Textarea
            id="escalate-reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
