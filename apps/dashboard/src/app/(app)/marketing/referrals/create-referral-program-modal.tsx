"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { ReferralRewardLedger } from "@rkpr/contracts";

import { useCreateReferralProgram } from "@/lib/hooks/use-referrals";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CurrencyInput } from "@/components/forms/currency-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function CreateReferralProgramModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const createProgram = useCreateReferralProgram();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [rewardLedger, setRewardLedger] = useState<ReferralRewardLedger>("loyalty_points");
  const [referrerReward, setReferrerReward] = useState("");
  const [refereeReward, setRefereeReward] = useState("");
  const [rewardHoldDays, setRewardHoldDays] = useState("0");
  const [error, setError] = useState<string | null>(null);

  const isMoney = rewardLedger === "internal_credit";

  function reset() {
    setCode("");
    setName("");
    setRewardLedger("loyalty_points");
    setReferrerReward("");
    setRefereeReward("");
    setRewardHoldDays("0");
    setError(null);
  }

  function toAmount(raw: string): number {
    const value = Number(raw);
    return isMoney ? Math.round(value * 100) : Math.round(value);
  }

  const canSubmit =
    code.trim() &&
    name.trim() &&
    referrerReward.trim() &&
    refereeReward.trim() &&
    Number.isFinite(Number(referrerReward)) &&
    Number.isFinite(Number(refereeReward)) &&
    !createProgram.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New referral program"
      description="Starts as a draft — activate it once the reward configuration is ready."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              createProgram.mutate(
                {
                  code: code.trim(),
                  name: name.trim(),
                  reward_ledger: rewardLedger,
                  referrer_reward_amount: toAmount(referrerReward),
                  referee_reward_amount: toAmount(refereeReward),
                  reward_hold_days: Math.max(0, Math.round(Number(rewardHoldDays) || 0)),
                },
                {
                  onSuccess: (response) => {
                    reset();
                    onOpenChange(false);
                    router.push(`/marketing/referrals/${response.data.id}`);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the program."),
                },
              );
            }}
          >
            {createProgram.isPending ? "Creating…" : "Create draft"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="referral-code">Code</Label>
            <Input id="referral-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="referral-name">Name</Label>
            <Input id="referral-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Reward ledger</Label>
          <Select
            value={rewardLedger}
            onValueChange={(v) => setRewardLedger(v as ReferralRewardLedger)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="loyalty_points">Loyalty points</SelectItem>
              <SelectItem value="internal_credit">Internal credit</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="referrer-reward">Referrer reward{isMoney ? "" : " (points)"}</Label>
            {isMoney ? (
              <CurrencyInput
                id="referrer-reward"
                value={referrerReward}
                onChange={(e) => setReferrerReward(e.target.value)}
              />
            ) : (
              <Input
                id="referrer-reward"
                type="number"
                min={0}
                value={referrerReward}
                onChange={(e) => setReferrerReward(e.target.value)}
              />
            )}
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="referee-reward">Referee reward{isMoney ? "" : " (points)"}</Label>
            {isMoney ? (
              <CurrencyInput
                id="referee-reward"
                value={refereeReward}
                onChange={(e) => setRefereeReward(e.target.value)}
              />
            ) : (
              <Input
                id="referee-reward"
                type="number"
                min={0}
                value={refereeReward}
                onChange={(e) => setRefereeReward(e.target.value)}
              />
            )}
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="reward-hold-days">Reward hold days</Label>
          <Input
            id="reward-hold-days"
            type="number"
            min={0}
            value={rewardHoldDays}
            onChange={(e) => setRewardHoldDays(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
