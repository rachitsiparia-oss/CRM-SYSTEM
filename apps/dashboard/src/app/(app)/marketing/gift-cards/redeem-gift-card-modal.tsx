"use client";

import { useState } from "react";

import { useRedeemGiftCard } from "@/lib/hooks/use-gift-cards";
import { ApiError } from "@/lib/api/errors";
import { formatMinorUnits } from "@/lib/crm-display";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CurrencyInput } from "@/components/forms/currency-input";

export function RedeemGiftCardModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const redeem = useRedeemGiftCard();

  const [code, setCode] = useState("");
  const [pin, setPin] = useState("");
  const [amountRupees, setAmountRupees] = useState("");
  const [orderId, setOrderId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [balanceAfter, setBalanceAfter] = useState<number | null>(null);

  function reset() {
    setCode("");
    setPin("");
    setAmountRupees("");
    setOrderId("");
    setError(null);
    setBalanceAfter(null);
  }

  const canSubmit =
    code.trim() && amountRupees.trim() && Number(amountRupees) > 0 && !redeem.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Redeem gift card"
      description="Enter the code the customer presents to apply it against an order."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              setError(null);
              redeem.mutate(
                {
                  code: code.trim(),
                  pin: pin.trim() || null,
                  amount_minor: Math.round(Number(amountRupees) * 100),
                  order_id: orderId.trim() || null,
                  idempotency_key: crypto.randomUUID(),
                },
                {
                  onSuccess: (response) => {
                    setBalanceAfter(response.data.balance_after_minor);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not redeem this gift card."),
                },
              );
            }}
          >
            {redeem.isPending ? "Redeeming…" : "Redeem"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        {balanceAfter !== null && (
          <p className="text-success text-sm">
            Redeemed. Remaining balance: {formatMinorUnits(balanceAfter)}
          </p>
        )}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="redeem-code">Gift card code</Label>
          <Input
            id="redeem-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="XXXX-XXXX-XXXX-XXXX"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="redeem-pin">PIN (if set)</Label>
          <Input id="redeem-pin" value={pin} onChange={(e) => setPin(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="redeem-amount">Amount to redeem</Label>
          <CurrencyInput
            id="redeem-amount"
            value={amountRupees}
            onChange={(e) => setAmountRupees(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="redeem-order-id">Order ID (optional)</Label>
          <Input id="redeem-order-id" value={orderId} onChange={(e) => setOrderId(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
