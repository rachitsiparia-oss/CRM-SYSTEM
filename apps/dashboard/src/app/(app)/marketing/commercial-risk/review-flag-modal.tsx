"use client";

import { useState } from "react";
import type { CommercialRiskFlagStatus } from "@rkpr/contracts";

import { useReviewCommercialRiskFlag } from "@/lib/hooks/use-commercial-risk";
import { ApiError } from "@/lib/api/errors";
import { humanize } from "@/lib/crm-display";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type ReviewTarget = "reviewing" | "resolved" | "dismissed";
const TARGETS: ReviewTarget[] = ["reviewing", "resolved", "dismissed"];

export function ReviewFlagModal({
  open,
  onOpenChange,
  flagId,
  currentStatus,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  flagId: string;
  currentStatus: CommercialRiskFlagStatus;
}) {
  const review = useReviewCommercialRiskFlag(flagId);
  const [target, setTarget] = useState<ReviewTarget>(
    currentStatus === "open" ? "reviewing" : "resolved",
  );
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTarget(currentStatus === "open" ? "reviewing" : "resolved");
    setNote("");
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Review flagged event"
      description="Move this flag to a review state and optionally record a resolution note."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={review.isPending}
            onClick={() => {
              setError(null);
              review.mutate(
                { target_status: target, resolution_note: note.trim() || null },
                {
                  onSuccess: () => {
                    reset();
                    onOpenChange(false);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not update this flag."),
                },
              );
            }}
          >
            {review.isPending ? "Saving…" : "Save"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex flex-col gap-1.5">
          <Label>New status</Label>
          <Select value={target} onValueChange={(v) => setTarget(v as ReviewTarget)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TARGETS.map((t) => (
                <SelectItem key={t} value={t}>
                  {humanize(t)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="resolution-note">Resolution note (optional)</Label>
          <Textarea id="resolution-note" rows={3} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
      </div>
    </Modal>
  );
}
