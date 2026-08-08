"use client";

import { useState } from "react";

import { useAttributeReferral } from "@/lib/hooks/use-referrals";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function AttributeReferralModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const attribute = useAttributeReferral();
  const [code, setCode] = useState("");
  const [referredContact, setReferredContact] = useState("");
  const [referredCustomerId, setReferredCustomerId] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setCode("");
    setReferredContact("");
    setReferredCustomerId("");
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Attribute a referral"
      description="Manually record that a referred contact used a referral code."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!code.trim() || !referredContact.trim() || attribute.isPending}
            onClick={() => {
              attribute.mutate(
                {
                  code: code.trim(),
                  referred_contact: referredContact.trim(),
                  referred_customer_id: referredCustomerId.trim() || null,
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not attribute this referral."),
                },
              );
            }}
          >
            {attribute.isPending ? "Attributing…" : "Attribute"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="attribute-code">Referral code</Label>
          <Input id="attribute-code" value={code} onChange={(e) => setCode(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="attribute-contact">Referred contact (phone or email)</Label>
          <Input
            id="attribute-contact"
            value={referredContact}
            onChange={(e) => setReferredContact(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="attribute-customer-id">Referred customer ID (optional)</Label>
          <Input
            id="attribute-customer-id"
            value={referredCustomerId}
            onChange={(e) => setReferredCustomerId(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
