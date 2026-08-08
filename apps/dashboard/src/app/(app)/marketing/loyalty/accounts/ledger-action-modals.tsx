"use client";

import { useState } from "react";
import type { LoyaltyEarnInput, LoyaltyRedeemInput } from "@rkpr/contracts";

import { useAdjustLoyaltyPoints, useEarnLoyaltyPoints, useRedeemLoyaltyPoints } from "@/lib/hooks/use-loyalty";
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

interface AccountModalProps {
  accountId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const EARN_ENTRY_TYPES: LoyaltyEarnInput["entry_type"][] = [
  "earn_manual",
  "earn_campaign",
  "earn_order",
  "service_recovery_credit",
];

const REDEEM_ENTRY_TYPES: NonNullable<LoyaltyRedeemInput["entry_type"]>[] = [
  "redeem_reward",
  "redeem_order",
];

export function EarnPointsModal({ accountId, open, onOpenChange }: AccountModalProps) {
  const earn = useEarnLoyaltyPoints();
  const [entryType, setEntryType] = useState<LoyaltyEarnInput["entry_type"]>("earn_manual");
  const [points, setPoints] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const pointsNumber = Number(points);
  const isValid = points.trim() && Number.isFinite(pointsNumber) && pointsNumber > 0;

  function reset() {
    setEntryType("earn_manual");
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
      title="Earn points"
      description="Manually credit points to this account."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!isValid || earn.isPending}
            onClick={() => {
              setError(null);
              earn.mutate(
                {
                  account_id: accountId,
                  entry_type: entryType,
                  points: pointsNumber,
                  description: description.trim() || null,
                  idempotency_key: crypto.randomUUID(),
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not earn points."),
                },
              );
            }}
          >
            Earn points
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Entry type</Label>
            <Select
              value={entryType}
              onValueChange={(v) => setEntryType(v as LoyaltyEarnInput["entry_type"])}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EARN_ENTRY_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.replace(/_/g, " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="earn-points">Points</Label>
            <Input
              id="earn-points"
              type="number"
              min={1}
              value={points}
              onChange={(e) => setPoints(e.target.value)}
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="earn-description">Description</Label>
          <Input
            id="earn-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}

export function RedeemPointsModal({ accountId, open, onOpenChange }: AccountModalProps) {
  const redeem = useRedeemLoyaltyPoints();
  const [entryType, setEntryType] = useState<NonNullable<LoyaltyRedeemInput["entry_type"]>>(
    "redeem_reward",
  );
  const [points, setPoints] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const pointsNumber = Number(points);
  const isValid = points.trim() && Number.isFinite(pointsNumber) && pointsNumber > 0;

  function reset() {
    setEntryType("redeem_reward");
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
      title="Redeem points"
      description="Deducts points from this account's balance."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!isValid || redeem.isPending}
            onClick={() => {
              setError(null);
              redeem.mutate(
                {
                  account_id: accountId,
                  entry_type: entryType,
                  points: pointsNumber,
                  description: description.trim() || null,
                  idempotency_key: crypto.randomUUID(),
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not redeem points."),
                },
              );
            }}
          >
            Redeem points
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Entry type</Label>
            <Select
              value={entryType}
              onValueChange={(v) => setEntryType(v as NonNullable<LoyaltyRedeemInput["entry_type"]>)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {REDEEM_ENTRY_TYPES.map((type) => (
                  <SelectItem key={type} value={type}>
                    {type.replace(/_/g, " ")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="redeem-points">Points</Label>
            <Input
              id="redeem-points"
              type="number"
              min={1}
              value={points}
              onChange={(e) => setPoints(e.target.value)}
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="redeem-description">Description</Label>
          <Input
            id="redeem-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}

export function AdjustPointsModal({ accountId, open, onOpenChange }: AccountModalProps) {
  const adjust = useAdjustLoyaltyPoints();
  const [pointsDelta, setPointsDelta] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const deltaNumber = Number(pointsDelta);
  const isValid = pointsDelta.trim() && Number.isFinite(deltaNumber) && deltaNumber !== 0 && reason.trim();

  function reset() {
    setPointsDelta("");
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
      title="Adjust points"
      description="A signed correction — use a negative value to remove points. Requires a reason for audit."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!isValid || adjust.isPending}
            onClick={() => {
              setError(null);
              adjust.mutate(
                {
                  account_id: accountId,
                  points_delta: deltaNumber,
                  reason: reason.trim(),
                  idempotency_key: crypto.randomUUID(),
                },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not adjust points."),
                },
              );
            }}
          >
            Apply adjustment
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="adjust-delta">Points delta</Label>
          <Input
            id="adjust-delta"
            type="number"
            value={pointsDelta}
            onChange={(e) => setPointsDelta(e.target.value)}
            placeholder="e.g. -50 or 100"
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="adjust-reason">Reason</Label>
          <Input id="adjust-reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
