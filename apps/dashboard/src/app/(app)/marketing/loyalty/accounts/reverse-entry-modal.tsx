"use client";

import { useState } from "react";

import { useReverseLoyaltyEntry } from "@/lib/hooks/use-loyalty";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ReverseEntryModal({
  entryId,
  open,
  onOpenChange,
}: {
  entryId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const reverse = useReverseLoyaltyEntry();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setReason("");
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Reverse ledger entry"
      description="Creates an offsetting entry — the original entry is never edited or deleted."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!entryId || !reason.trim() || reverse.isPending}
            onClick={() => {
              if (!entryId) return;
              setError(null);
              reverse.mutate(
                { entry_id: entryId, reason: reason.trim(), idempotency_key: crypto.randomUUID() },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not reverse this entry."),
                },
              );
            }}
          >
            Reverse entry
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="reverse-reason">Reason</Label>
          <Input id="reverse-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
