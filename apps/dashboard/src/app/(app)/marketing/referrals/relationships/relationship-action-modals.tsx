"use client";

import { useState } from "react";

import {
  useQualifyReferral,
  useRejectReferral,
  useRewardReferral,
} from "@/lib/hooks/use-referrals";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { ConfirmDialog } from "@/components/modals/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function QualifyReferralModal({
  open,
  onOpenChange,
  relationshipId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  relationshipId: string;
}) {
  const qualify = useQualifyReferral(relationshipId);
  const [orderId, setOrderId] = useState("");
  const [error, setError] = useState<string | null>(null);

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setOrderId("");
          setError(null);
        }
        onOpenChange(next);
      }}
      title="Qualify referral"
      description="Record the qualifying order that made this referral eligible for a reward."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!orderId.trim() || qualify.isPending}
            onClick={() => {
              qualify.mutate(orderId.trim(), {
                onSuccess: () => {
                  setOrderId("");
                  onOpenChange(false);
                },
                onError: (err) =>
                  setError(err instanceof ApiError ? err.message : "Could not qualify this referral."),
              });
            }}
          >
            {qualify.isPending ? "Qualifying…" : "Qualify"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="qualifying-order-id">Qualifying order ID</Label>
          <Input id="qualifying-order-id" value={orderId} onChange={(e) => setOrderId(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}

export function RejectReferralModal({
  open,
  onOpenChange,
  relationshipId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  relationshipId: string;
}) {
  const reject = useRejectReferral(relationshipId);
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
      title="Reject referral"
      description="This relationship will be marked rejected and will not earn a reward."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={!reason.trim() || reject.isPending}
            onClick={() => {
              reject.mutate(reason.trim(), {
                onSuccess: () => {
                  setReason("");
                  onOpenChange(false);
                },
                onError: (err) =>
                  setError(err instanceof ApiError ? err.message : "Could not reject this referral."),
              });
            }}
          >
            {reject.isPending ? "Rejecting…" : "Reject"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="reject-reason">Reason</Label>
          <Textarea id="reject-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}

export function RewardReferralDialog({
  open,
  onOpenChange,
  relationshipId,
  onError,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  relationshipId: string;
  onError: (message: string) => void;
}) {
  const reward = useRewardReferral(relationshipId);

  return (
    <ConfirmDialog
      open={open}
      onOpenChange={onOpenChange}
      variant="confirm"
      title="Reward this referral?"
      description="Both the referrer and referee rewards will be posted to their configured ledger."
      confirmLabel="Reward"
      onConfirm={async () => {
        try {
          await reward.mutateAsync();
        } catch (err) {
          onError(err instanceof ApiError ? err.message : "Could not reward this referral.");
        }
      }}
    />
  );
}
