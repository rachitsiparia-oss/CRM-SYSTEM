"use client";

import { useState } from "react";

import { useAdjustGiftCard } from "@/lib/hooks/use-gift-cards";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CurrencyInput } from "@/components/forms/currency-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function AdjustBalanceModal({
  open,
  onOpenChange,
  giftCardId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  giftCardId: string;
}) {
  const adjust = useAdjustGiftCard(giftCardId);

  const [direction, setDirection] = useState<"increase" | "decrease">("increase");
  const [amountRupees, setAmountRupees] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setDirection("increase");
    setAmountRupees("");
    setReason("");
    setError(null);
  }

  const canSubmit = amountRupees.trim() && Number(amountRupees) > 0 && reason.trim() && !adjust.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Adjust balance"
      description="Manually correct this gift card's balance. Every adjustment is recorded in the ledger."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              setError(null);
              const magnitude = Math.round(Number(amountRupees) * 100);
              adjust.mutate(
                {
                  amount_delta_minor: direction === "increase" ? magnitude : -magnitude,
                  reason: reason.trim(),
                  idempotency_key: crypto.randomUUID(),
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not adjust the balance."),
                },
              );
            }}
          >
            {adjust.isPending ? "Adjusting…" : "Adjust"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label>Direction</Label>
          <Select value={direction} onValueChange={(v) => setDirection(v as "increase" | "decrease")}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="increase">Increase balance</SelectItem>
              <SelectItem value="decrease">Decrease balance</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="adjust-amount">Amount</Label>
          <CurrencyInput
            id="adjust-amount"
            value={amountRupees}
            onChange={(e) => setAmountRupees(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="adjust-reason">Reason</Label>
          <Textarea id="adjust-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
