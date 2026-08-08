"use client";

import { useState } from "react";

import { useRedeemCustomerCredit } from "@/lib/hooks/use-customer-credit";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { CurrencyInput } from "@/components/forms/currency-input";

export function RedeemCreditModal({
  open,
  onOpenChange,
  accountId,
  availableBalanceMinor,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accountId: string;
  availableBalanceMinor: number;
}) {
  const redeemCredit = useRedeemCustomerCredit();

  const [amountRupees, setAmountRupees] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setAmountRupees("");
    setSourceId("");
    setReason("");
    setError(null);
  }

  const amountMinor = Math.round(Number(amountRupees || "0") * 100);
  const canSubmit =
    amountRupees.trim() &&
    amountMinor > 0 &&
    amountMinor <= availableBalanceMinor &&
    !redeemCredit.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Redeem internal credit"
      description="Applies credit from this account, typically against an order."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              setError(null);
              redeemCredit.mutate(
                {
                  account_id: accountId,
                  amount_minor: amountMinor,
                  source_type: sourceId.trim() ? "order" : null,
                  source_id: sourceId.trim() || null,
                  reason: reason.trim() || null,
                  idempotency_key: crypto.randomUUID(),
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not redeem credit."),
                },
              );
            }}
          >
            {redeemCredit.isPending ? "Redeeming…" : "Redeem"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="redeem-credit-amount">Amount</Label>
          <CurrencyInput
            id="redeem-credit-amount"
            value={amountRupees}
            onChange={(e) => setAmountRupees(e.target.value)}
          />
          {amountMinor > availableBalanceMinor && (
            <p className="text-destructive text-xs">Amount exceeds the available balance.</p>
          )}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="redeem-credit-order">Order ID (optional)</Label>
          <Input id="redeem-credit-order" value={sourceId} onChange={(e) => setSourceId(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="redeem-credit-reason">Notes (optional)</Label>
          <Textarea
            id="redeem-credit-reason"
            rows={2}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
