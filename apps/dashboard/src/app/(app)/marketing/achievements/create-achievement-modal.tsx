"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { AchievementRewardLedger, CommercialRuleFact, RuleOperator } from "@rkpr/contracts";

import { useCreateAchievement } from "@/lib/hooks/use-achievements";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { SingleConditionBuilder, buildConditionValue } from "./condition-builder";

export function CreateAchievementModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const createAchievement = useCreateAchievement();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [fact, setFact] = useState<CommercialRuleFact>("customer.completed_order_count");
  const [operator, setOperator] = useState<RuleOperator>("gte");
  const [valueText, setValueText] = useState("");
  const [rewardLedger, setRewardLedger] = useState<AchievementRewardLedger>("none");
  const [rewardAmount, setRewardAmount] = useState("");
  const [isRepeatable, setIsRepeatable] = useState(false);
  const [cooldownDays, setCooldownDays] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isMoney = rewardLedger === "internal_credit";
  const needsValue = operator !== "is_true" && operator !== "is_false";

  function reset() {
    setCode("");
    setName("");
    setDescription("");
    setFact("customer.completed_order_count");
    setOperator("gte");
    setValueText("");
    setRewardLedger("none");
    setRewardAmount("");
    setIsRepeatable(false);
    setCooldownDays("");
    setError(null);
  }

  const canSubmit =
    code.trim() &&
    name.trim() &&
    (!needsValue || valueText.trim()) &&
    (rewardLedger === "none" || (rewardAmount.trim() && Number.isFinite(Number(rewardAmount)))) &&
    !createAchievement.isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New achievement"
      description="Define a single fact-based condition. Customers who cross it are awarded automatically."
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              const amount = rewardAmount.trim()
                ? isMoney
                  ? Math.round(Number(rewardAmount) * 100)
                  : Math.round(Number(rewardAmount))
                : null;
              createAchievement.mutate(
                {
                  code: code.trim(),
                  name: name.trim(),
                  description: description.trim() || null,
                  condition: {
                    kind: "condition",
                    fact,
                    operator,
                    value: buildConditionValue(operator, valueText),
                  },
                  reward_ledger: rewardLedger,
                  reward_amount: rewardLedger === "none" ? null : amount,
                  is_repeatable: isRepeatable,
                  cooldown_days: isRepeatable && cooldownDays.trim() ? Math.round(Number(cooldownDays)) : null,
                },
                {
                  onSuccess: (response) => {
                    reset();
                    onOpenChange(false);
                    router.push(`/marketing/achievements/${response.data.id}`);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the achievement."),
                },
              );
            }}
          >
            {createAchievement.isPending ? "Creating…" : "Create achievement"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="achievement-code">Code</Label>
            <Input id="achievement-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="achievement-name">Name</Label>
            <Input id="achievement-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="achievement-description">Description</Label>
          <Textarea
            id="achievement-description"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Condition</Label>
          <SingleConditionBuilder
            fact={fact}
            operator={operator}
            valueText={valueText}
            onFactChange={setFact}
            onOperatorChange={setOperator}
            onValueTextChange={setValueText}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Reward ledger</Label>
            <Select
              value={rewardLedger}
              onValueChange={(v) => setRewardLedger(v as AchievementRewardLedger)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No reward</SelectItem>
                <SelectItem value="loyalty_points">Loyalty points</SelectItem>
                <SelectItem value="internal_credit">Internal credit</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {rewardLedger !== "none" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="achievement-reward-amount">Reward amount{isMoney ? "" : " (points)"}</Label>
              {isMoney ? (
                <CurrencyInput
                  id="achievement-reward-amount"
                  value={rewardAmount}
                  onChange={(e) => setRewardAmount(e.target.value)}
                />
              ) : (
                <Input
                  id="achievement-reward-amount"
                  type="number"
                  min={0}
                  value={rewardAmount}
                  onChange={(e) => setRewardAmount(e.target.value)}
                />
              )}
            </div>
          )}
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={isRepeatable}
            onChange={(e) => setIsRepeatable(e.target.checked)}
          />
          Repeatable — a customer can earn this more than once
        </label>

        {isRepeatable && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="achievement-cooldown">Cooldown days between awards</Label>
            <Input
              id="achievement-cooldown"
              type="number"
              min={0}
              value={cooldownDays}
              onChange={(e) => setCooldownDays(e.target.value)}
            />
          </div>
        )}
      </div>
    </Modal>
  );
}
