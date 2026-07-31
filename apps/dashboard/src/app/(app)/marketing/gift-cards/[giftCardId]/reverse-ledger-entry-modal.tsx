"use client";

import { useState } from "react";

import { useReverseGiftCardEntry } from "@/lib/hooks/use-gift-cards";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function ReverseLedgerEntryModal({
  open,
  onOpenChange,
  entryId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  entryId: string;
}) {
  const reverseEntry = useReverseGiftCardEntry();
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
      title="Reverse ledger entry"
      description="This posts an offsetting entry — the original entry is preserved for audit history."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!reason.trim() || reverseEntry.isPending}
            onClick={() => {
              setError(null);
              reverseEntry.mutate(
                { entry_id: entryId, reason: reason.trim(), idempotency_key: crypto.randomUUID() },
                {
                  onSuccess: () => {
                    setReason("");
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not reverse this entry."),
                },
              );
            }}
          >
            {reverseEntry.isPending ? "Reversing…" : "Reverse"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="reverse-reason">Reason</Label>
          <Textarea id="reverse-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
