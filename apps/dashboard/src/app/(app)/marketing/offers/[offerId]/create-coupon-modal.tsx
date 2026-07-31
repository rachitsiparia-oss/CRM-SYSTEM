"use client";

import { useState } from "react";

import { useCreateCoupon } from "@/lib/hooks/use-offers";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";

export function CreateCouponModal({
  offerId,
  open,
  onOpenChange,
}: {
  offerId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createCoupon = useCreateCoupon(offerId);

  const [code, setCode] = useState("");
  const [isReusable, setIsReusable] = useState(true);
  const [redemptionLimit, setRedemptionLimit] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setCode("");
    setIsReusable(true);
    setRedemptionLimit("");
    setExpiresAt("");
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New coupon"
      description="A redeemable code for this offer."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!code.trim() || createCoupon.isPending}
            onClick={() => {
              setError(null);
              createCoupon.mutate(
                {
                  code: code.trim().toUpperCase(),
                  is_reusable: isReusable,
                  redemption_limit: redemptionLimit.trim() ? Number(redemptionLimit) : null,
                  expires_at: expiresAt.trim() ? new Date(expiresAt).toISOString() : null,
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the coupon."),
                },
              );
            }}
          >
            Create coupon
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="coupon-code">Code</Label>
          <Input
            id="coupon-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="e.g. WELCOME10"
          />
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            id="coupon-reusable"
            checked={isReusable}
            onCheckedChange={(checked) => setIsReusable(checked === true)}
          />
          <Label htmlFor="coupon-reusable" className="text-sm font-normal">
            Reusable across multiple customers
          </Label>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="coupon-limit">Redemption limit</Label>
            <Input
              id="coupon-limit"
              type="number"
              min={1}
              value={redemptionLimit}
              onChange={(e) => setRedemptionLimit(e.target.value)}
              placeholder="Unlimited"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="coupon-expires">Expires at</Label>
            <Input
              id="coupon-expires"
              type="datetime-local"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
            />
          </div>
        </div>
      </div>
    </Modal>
  );
}
