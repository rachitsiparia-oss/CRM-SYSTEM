"use client";

import { useState } from "react";

import { useAssignLoyaltyTier, useLoyaltyTiers } from "@/lib/hooks/use-loyalty";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function AssignTierModal({
  accountId,
  programId,
  open,
  onOpenChange,
}: {
  accountId: string;
  programId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: tiers } = useLoyaltyTiers(programId);
  const assignTier = useAssignLoyaltyTier(accountId);

  const [tierId, setTierId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTierId("");
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
      title="Assign tier"
      description="Manually overrides this account's current tier."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!tierId || !reason.trim() || assignTier.isPending}
            onClick={() => {
              setError(null);
              assignTier.mutate(
                { tier_id: tierId, reason: reason.trim() },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not assign this tier."),
                },
              );
            }}
          >
            Assign tier
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label>Tier</Label>
          <Select value={tierId} onValueChange={setTierId}>
            <SelectTrigger>
              <SelectValue placeholder="Select a tier" />
            </SelectTrigger>
            <SelectContent>
              {(tiers ?? []).map((tier) => (
                <SelectItem key={tier.id} value={tier.id}>
                  {tier.name} (rank {tier.rank})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="assign-tier-reason">Reason</Label>
          <Input
            id="assign-tier-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
