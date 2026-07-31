"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { SegmentType } from "@rkpr/contracts";

import { useCreateSegment } from "@/lib/hooks/use-segments";
import { ApiError } from "@/lib/api/errors";
import {
  DEFAULT_RULE_CONDITION_DRAFT,
  RuleConditionInput,
  buildRuleCondition,
  type RuleConditionDraft,
} from "@/components/forms/rule-condition-input";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function CreateSegmentModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const createSegment = useCreateSegment();

  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [segmentType, setSegmentType] = useState<SegmentType>("dynamic");
  const [ruleDraft, setRuleDraft] = useState<RuleConditionDraft>(DEFAULT_RULE_CONDITION_DRAFT);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setCode("");
    setName("");
    setDescription("");
    setSegmentType("dynamic");
    setRuleDraft(DEFAULT_RULE_CONDITION_DRAFT);
    setError(null);
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="New segment"
      description="Dynamic segments are evaluated by rule; static segments are curated by hand."
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!code.trim() || !name.trim() || createSegment.isPending}
            onClick={() => {
              setError(null);
              createSegment.mutate(
                {
                  code: code.trim(),
                  name: name.trim(),
                  description: description.trim() || null,
                  segment_type: segmentType,
                  rule_definition: segmentType === "dynamic" ? buildRuleCondition(ruleDraft) : null,
                },
                {
                  onSuccess: (response) => {
                    reset();
                    onOpenChange(false);
                    router.push(`/marketing/segments/${response.data.id}`);
                  },
                  onError: (err) =>
                    setError(err instanceof ApiError ? err.message : "Could not create the segment."),
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
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="segment-code">Code</Label>
            <Input id="segment-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Type</Label>
            <Select value={segmentType} onValueChange={(v) => setSegmentType(v as SegmentType)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="dynamic">Dynamic (rule-evaluated)</SelectItem>
                <SelectItem value="static">Static (manually curated)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="segment-name">Name</Label>
          <Input id="segment-name" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="segment-description">Description</Label>
          <Textarea
            id="segment-description"
            rows={2}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
        {segmentType === "dynamic" && (
          <div className="flex flex-col gap-1.5">
            <Label>Membership rule</Label>
            <p className="text-muted-foreground text-xs">
              A single condition — customers matching it are added on the next refresh.
            </p>
            <RuleConditionInput draft={ruleDraft} onChange={setRuleDraft} />
          </div>
        )}
      </div>
    </Modal>
  );
}
