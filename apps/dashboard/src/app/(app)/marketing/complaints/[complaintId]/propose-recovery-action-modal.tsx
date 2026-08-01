"use client";

import { useState } from "react";
import type { RecoveryType } from "@rkpr/contracts";

import { useProposeRecoveryAction } from "@/lib/hooks/use-service-recovery";
import { humanize } from "@/lib/crm-display";
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

const RECOVERY_TYPES: RecoveryType[] = [
  "apology_only",
  "replacement",
  "refund_request",
  "approved_refund",
  "discount",
  "coupon",
  "loyalty_credit",
  "complimentary_item",
  "manager_follow_up",
  "operational_correction",
];
const MONEY_TYPES: RecoveryType[] = [
  "refund_request",
  "approved_refund",
  "discount",
  "complimentary_item",
];
const POINTS_TYPES: RecoveryType[] = ["loyalty_credit"];

export function ProposeRecoveryActionModal({
  complaintId,
  open,
  onOpenChange,
}: {
  complaintId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const proposeAction = useProposeRecoveryAction(complaintId);
  const [recoveryType, setRecoveryType] = useState<RecoveryType>("apology_only");
  const [valueMinor, setValueMinor] = useState("");
  const [points, setPoints] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isMoney = MONEY_TYPES.includes(recoveryType);
  const isPoints = POINTS_TYPES.includes(recoveryType);
  const canSubmit =
    description.trim() &&
    (!isMoney || valueMinor.trim()) &&
    (!isPoints || points.trim()) &&
    !proposeAction.isPending;

  function reset() {
    setRecoveryType("apology_only");
    setValueMinor("");
    setPoints("");
    setDescription("");
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Propose recovery action"
      description="Compensation is executed through the existing loyalty, credit, or order module — never mutated directly here."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              setError(null);
              proposeAction.mutate(
                {
                  recovery_type: recoveryType,
                  value_minor: isMoney ? Math.round(Number(valueMinor) * 100) : null,
                  points: isPoints ? Math.round(Number(points)) : null,
                  description: description.trim(),
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not propose this action."),
                },
              );
            }}
          >
            {proposeAction.isPending ? "Proposing…" : "Propose"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}

        <div className="flex flex-col gap-1.5">
          <Label>Recovery type</Label>
          <Select value={recoveryType} onValueChange={(v) => setRecoveryType(v as RecoveryType)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {RECOVERY_TYPES.map((value) => (
                <SelectItem key={value} value={value}>
                  {humanize(value)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {isMoney && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="recovery-value">Value</Label>
            <CurrencyInput
              id="recovery-value"
              value={valueMinor}
              onChange={(e) => setValueMinor(e.target.value)}
            />
          </div>
        )}

        {isPoints && (
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="recovery-points">Points</Label>
            <Input
              id="recovery-points"
              type="number"
              min={0}
              value={points}
              onChange={(e) => setPoints(e.target.value)}
            />
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="recovery-description">Description</Label>
          <Textarea
            id="recovery-description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
