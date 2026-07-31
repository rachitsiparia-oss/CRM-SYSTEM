"use client";

import { useState } from "react";
import type { TierQualificationMetric } from "@rkpr/contracts";

import { useCreateLoyaltyTier } from "@/lib/hooks/use-loyalty";
import { ApiError } from "@/lib/api/errors";
import { humanize } from "@/lib/crm-display";
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

const QUALIFICATION_METRICS: TierQualificationMetric[] = [
  "lifetime_spend",
  "rolling_spend",
  "points_earned",
  "completed_orders",
  "visits",
  "manual",
];

export function CreateTierModal({
  programId,
  open,
  onOpenChange,
}: {
  programId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createTier = useCreateLoyaltyTier(programId);

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [rank, setRank] = useState("1");
  const [qualificationMetric, setQualificationMetric] =
    useState<TierQualificationMetric>("lifetime_spend");
  const [threshold, setThreshold] = useState("0");
  const [pointsMultiplier, setPointsMultiplier] = useState("1");
  const [benefitsSummary, setBenefitsSummary] = useState("");
  const [error, setError] = useState<string | null>(null);

  const rankNumber = Number(rank);
  const isValid = code.trim() && name.trim() && Number.isFinite(rankNumber) && threshold.trim();

  function reset() {
    setCode("");
    setName("");
    setRank("1");
    setQualificationMetric("lifetime_spend");
    setThreshold("0");
    setPointsMultiplier("1");
    setBenefitsSummary("");
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New loyalty tier"
      description="Rank determines ordering — lower ranks qualify first."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!isValid || createTier.isPending}
            onClick={() => {
              setError(null);
              createTier.mutate(
                {
                  code: code.trim(),
                  name: name.trim(),
                  rank: rankNumber,
                  qualification_metric: qualificationMetric,
                  threshold: threshold.trim(),
                  points_multiplier: pointsMultiplier.trim() || undefined,
                  benefits_summary: benefitsSummary.trim() || null,
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the tier."),
                },
              );
            }}
          >
            Create tier
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="tier-code">Code</Label>
            <Input id="tier-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="GOLD" />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="tier-name">Name</Label>
            <Input id="tier-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="tier-rank">Rank</Label>
            <Input
              id="tier-rank"
              type="number"
              min={1}
              value={rank}
              onChange={(e) => setRank(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Qualification metric</Label>
            <Select
              value={qualificationMetric}
              onValueChange={(v) => setQualificationMetric(v as TierQualificationMetric)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {QUALIFICATION_METRICS.map((metric) => (
                  <SelectItem key={metric} value={metric}>
                    {humanize(metric)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="tier-threshold">Threshold</Label>
            <Input
              id="tier-threshold"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              placeholder="e.g. 5000"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="tier-multiplier">Points multiplier</Label>
            <Input
              id="tier-multiplier"
              value={pointsMultiplier}
              onChange={(e) => setPointsMultiplier(e.target.value)}
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="tier-benefits">Benefits summary</Label>
          <Input
            id="tier-benefits"
            value={benefitsSummary}
            onChange={(e) => setBenefitsSummary(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
