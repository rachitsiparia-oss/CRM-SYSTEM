"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import type { Achievement, AchievementRewardLedger, CommercialRuleFact, RuleOperator } from "@rkpr/contracts";

import { useAchievementDetail, useUpdateAchievement } from "@/lib/hooks/use-achievements";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatDateTime, formatMinorUnits, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { PageHeader } from "@/components/page-header";
import { PageSkeleton } from "@/components/skeletons/page-skeleton";
import { ErrorState } from "@/components/error-state";
import { StatusBadge } from "@/components/status-badge";
import { SectionCard } from "@/components/section-card";
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
import {
  SingleConditionBuilder,
  buildConditionValue,
  isSingleCondition,
  summarizeRuleNode,
  valueToInputText,
} from "../condition-builder";

export function AchievementDetail({ achievementId }: { achievementId: string }) {
  const { data: currentUser } = useCurrentUser();
  const { data: achievement, isLoading, isError, refetch } = useAchievementDetail(achievementId);
  const canManage = hasPermission(currentUser, "achievements.manage");

  if (isLoading) {
    return (
      <div className="flex-1 p-6">
        <PageSkeleton />
      </div>
    );
  }

  if (isError || !achievement) {
    return (
      <div className="flex-1 p-6">
        <ErrorState variant="404" title="Achievement not found" onRetry={() => void refetch()} />
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-6 p-6">
      <div>
        <Link
          href="/marketing/achievements"
          className="text-muted-foreground inline-flex items-center gap-1 text-sm hover:underline"
        >
          <ArrowLeft className="size-3.5" />
          Achievements
        </Link>
      </div>

      <PageHeader
        title={achievement.name}
        description={achievement.code}
        actions={
          <div className="flex flex-wrap gap-2">
            <StatusBadge
              label={achievement.is_active ? "Active" : "Inactive"}
              tone={achievement.is_active ? "success" : "neutral"}
            />
            {achievement.is_hidden && <StatusBadge label="Hidden" tone="info" />}
            {achievement.is_repeatable && <StatusBadge label="Repeatable" tone="info" />}
          </div>
        }
      />

      <SectionCard title="Condition" description="A customer is awarded when this fact matches.">
        <p className="text-sm">{summarizeRuleNode(achievement.condition)}</p>
        {!isSingleCondition(achievement.condition) && (
          <p className="text-muted-foreground mt-2 text-xs">
            This condition uses a nested rule group and cannot be edited from this simplified
            single-condition builder.
          </p>
        )}
      </SectionCard>

      {/* Keyed by achievement.id so the form's local editing state is
       * initialized fresh from props on navigation between achievements,
       * without syncing it back from a query result inside an effect
       * (react-hooks/set-state-in-effect — CLAUDE.md section 10's "avoid
       * unnecessary rerenders", the same "reset state via key" pattern
       * article-detail.tsx doesn't need only because it uses a single
       * uncontrolled field instead of a full form). */}
      <AchievementEditForm
        key={achievement.id}
        achievement={achievement}
        achievementId={achievementId}
        canManage={canManage}
      />

      <SectionCard title="Metadata">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground text-xs">Condition version</dt>
            <dd className="text-sm">{achievement.condition_version}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Created</dt>
            <dd className="text-sm">{formatDateTime(achievement.created_at)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground text-xs">Updated</dt>
            <dd className="text-sm">{formatDateTime(achievement.updated_at)}</dd>
          </div>
          {achievement.reward_ledger !== "none" && achievement.reward_amount !== null && (
            <div>
              <dt className="text-muted-foreground text-xs">Current reward</dt>
              <dd className="text-sm">
                {achievement.reward_ledger === "internal_credit"
                  ? formatMinorUnits(achievement.reward_amount)
                  : `${achievement.reward_amount} pts`}
              </dd>
            </div>
          )}
          <div>
            <dt className="text-muted-foreground text-xs">Reward ledger</dt>
            <dd className="text-sm">{humanize(achievement.reward_ledger)}</dd>
          </div>
        </dl>
      </SectionCard>
    </div>
  );
}

function AchievementEditForm({
  achievement,
  achievementId,
  canManage,
}: {
  achievement: Achievement;
  achievementId: string;
  canManage: boolean;
}) {
  const updateAchievement = useUpdateAchievement(achievementId);
  const conditionIsEditable = isSingleCondition(achievement.condition);

  const [name, setName] = useState(achievement.name);
  const [description, setDescription] = useState(achievement.description ?? "");
  const [isActive, setIsActive] = useState(achievement.is_active);
  const [isHidden, setIsHidden] = useState(achievement.is_hidden);
  const [rewardLedger, setRewardLedger] = useState<AchievementRewardLedger>(achievement.reward_ledger);
  const [rewardAmount, setRewardAmount] = useState(() =>
    achievement.reward_amount === null
      ? ""
      : achievement.reward_ledger === "internal_credit"
        ? String(achievement.reward_amount / 100)
        : String(achievement.reward_amount),
  );
  const [isRepeatable, setIsRepeatable] = useState(achievement.is_repeatable);
  const [cooldownDays, setCooldownDays] = useState(
    achievement.cooldown_days === null ? "" : String(achievement.cooldown_days),
  );
  const [fact, setFact] = useState<CommercialRuleFact>(() =>
    isSingleCondition(achievement.condition) ? achievement.condition.fact : "customer.completed_order_count",
  );
  const [operator, setOperator] = useState<RuleOperator>(() =>
    isSingleCondition(achievement.condition) ? achievement.condition.operator : "gte",
  );
  const [valueText, setValueText] = useState(() =>
    isSingleCondition(achievement.condition) ? valueToInputText(achievement.condition.value) : "",
  );
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const isMoney = rewardLedger === "internal_credit";

  return (
    <SectionCard
      title="Details and reward"
      description={canManage ? "Edit and save below." : "Requires achievements.manage to edit."}
    >
      <div className="flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
        {saved && !error && <p className="text-success text-sm">Changes saved.</p>}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="edit-name">Name</Label>
            <Input
              id="edit-name"
              disabled={!canManage}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Reward ledger</Label>
            <Select
              value={rewardLedger}
              onValueChange={(v) => setRewardLedger(v as AchievementRewardLedger)}
              disabled={!canManage}
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
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="edit-description">Description</Label>
          <Textarea
            id="edit-description"
            rows={2}
            disabled={!canManage}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {conditionIsEditable && (
          <div className="flex flex-col gap-1.5">
            <Label>Condition</Label>
            <SingleConditionBuilder
              fact={fact}
              operator={operator}
              valueText={valueText}
              onFactChange={setFact}
              onOperatorChange={setOperator}
              onValueTextChange={setValueText}
              disabled={!canManage}
            />
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {rewardLedger !== "none" && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="edit-reward-amount">Reward amount{isMoney ? "" : " (points)"}</Label>
              {isMoney ? (
                <CurrencyInput
                  id="edit-reward-amount"
                  disabled={!canManage}
                  value={rewardAmount}
                  onChange={(e) => setRewardAmount(e.target.value)}
                />
              ) : (
                <Input
                  id="edit-reward-amount"
                  type="number"
                  min={0}
                  disabled={!canManage}
                  value={rewardAmount}
                  onChange={(e) => setRewardAmount(e.target.value)}
                />
              )}
            </div>
          )}
          {isRepeatable && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="edit-cooldown">Cooldown days</Label>
              <Input
                id="edit-cooldown"
                type="number"
                min={0}
                disabled={!canManage}
                value={cooldownDays}
                onChange={(e) => setCooldownDays(e.target.value)}
              />
            </div>
          )}
        </div>

        <div className="flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              disabled={!canManage}
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            Active
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              disabled={!canManage}
              checked={isHidden}
              onChange={(e) => setIsHidden(e.target.checked)}
            />
            Hidden from customer-facing surfaces
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              disabled={!canManage}
              checked={isRepeatable}
              onChange={(e) => setIsRepeatable(e.target.checked)}
            />
            Repeatable
          </label>
        </div>

        {canManage && (
          <div>
            <Button
              disabled={!name.trim() || updateAchievement.isPending}
              onClick={() => {
                setError(null);
                setSaved(false);
                const amount = rewardAmount.trim()
                  ? isMoney
                    ? Math.round(Number(rewardAmount) * 100)
                    : Math.round(Number(rewardAmount))
                  : null;
                updateAchievement.mutate(
                  {
                    name: name.trim(),
                    description: description.trim() || null,
                    is_active: isActive,
                    is_hidden: isHidden,
                    reward_ledger: rewardLedger,
                    reward_amount: rewardLedger === "none" ? null : amount,
                    is_repeatable: isRepeatable,
                    cooldown_days:
                      isRepeatable && cooldownDays.trim() ? Math.round(Number(cooldownDays)) : null,
                    condition: conditionIsEditable
                      ? { kind: "condition", fact, operator, value: buildConditionValue(operator, valueText) }
                      : undefined,
                  },
                  {
                    onSuccess: () => setSaved(true),
                    onError: (err) =>
                      setError(err instanceof ApiError ? err.message : "Could not save changes."),
                  },
                );
              }}
            >
              {updateAchievement.isPending ? "Saving…" : "Save changes"}
            </Button>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
