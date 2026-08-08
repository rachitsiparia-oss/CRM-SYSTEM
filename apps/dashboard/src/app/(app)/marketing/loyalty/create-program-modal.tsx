"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { useCreateLoyaltyProgram } from "@/lib/hooks/use-loyalty";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function CreateProgramModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const createProgram = useCreateLoyaltyProgram();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [pointsDisplayName, setPointsDisplayName] = useState("points");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setCode("");
    setName("");
    setPointsDisplayName("points");
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
      title="New loyalty program"
      description="Starts as a draft — activate it once tiers and rules are configured."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!code.trim() || !name.trim() || createProgram.isPending}
            onClick={() => {
              setError(null);
              createProgram.mutate(
                {
                  code: code.trim(),
                  name: name.trim(),
                  points_display_name: pointsDisplayName.trim() || undefined,
                  description: description.trim() || null,
                },
                {
                  onSuccess: (response) => {
                    reset();
                    onOpenChange(false);
                    router.push(`/marketing/loyalty/programs/${response.data.id}`);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the program."),
                },
              );
            }}
          >
            Create draft
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && <p className="text-sm text-destructive">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="program-code">Code</Label>
            <Input
              id="program-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. RKPR_REWARDS"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="program-points-name">Points display name</Label>
            <Input
              id="program-points-name"
              value={pointsDisplayName}
              onChange={(e) => setPointsDisplayName(e.target.value)}
            />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="program-name">Name</Label>
          <Input id="program-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="program-description">Description</Label>
          <Textarea
            id="program-description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>
    </Modal>
  );
}
