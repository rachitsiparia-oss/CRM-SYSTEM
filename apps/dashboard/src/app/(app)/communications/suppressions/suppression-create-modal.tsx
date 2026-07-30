"use client";

import { useState } from "react";
import type { SuppressionDestinationType, SuppressionReason, SuppressionScope } from "@rkpr/contracts";

import { useCreateSuppression } from "@/lib/hooks/use-communications";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const DESTINATION_TYPES: SuppressionDestinationType[] = ["email", "phone"];
const REASONS: SuppressionReason[] = [
  "hard_bounce",
  "spam_complaint",
  "invalid_destination",
  "manual_block",
  "customer_request",
  "unsubscribed",
];
const SCOPES: SuppressionScope[] = ["all", "promotional_only"];

export function SuppressionCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createSuppression = useCreateSuppression();
  const [destinationType, setDestinationType] = useState<SuppressionDestinationType>("phone");
  const [destinationValue, setDestinationValue] = useState("");
  const [reason, setReason] = useState<SuppressionReason>("manual_block");
  const [scope, setScope] = useState<SuppressionScope>("all");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setDestinationType("phone");
    setDestinationValue("");
    setReason("manual_block");
    setScope("all");
    setNotes("");
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    try {
      await createSuppression.mutateAsync({
        destination_type: destinationType,
        destination_value: destinationValue.trim(),
        reason,
        scope,
        notes: notes.trim() || null,
      });
      reset();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The suppression could not be added.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Add a suppression"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!destinationValue.trim() || createSuppression.isPending} onClick={() => void handleSubmit()}>
            {createSuppression.isPending ? "Adding…" : "Add suppression"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <FormField label="Destination type" htmlFor="suppression-type">
          <Select value={destinationType} onValueChange={(value) => setDestinationType(value as SuppressionDestinationType)}>
            <SelectTrigger id="suppression-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DESTINATION_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {humanize(type)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Destination value" htmlFor="suppression-value">
          <Input
            id="suppression-value"
            value={destinationValue}
            onChange={(e) => setDestinationValue(e.target.value)}
            placeholder={destinationType === "phone" ? "+91XXXXXXXXXX" : "name@example.com"}
          />
        </FormField>
        <FormField label="Reason" htmlFor="suppression-reason">
          <Select value={reason} onValueChange={(value) => setReason(value as SuppressionReason)}>
            <SelectTrigger id="suppression-reason">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {REASONS.map((r) => (
                <SelectItem key={r} value={r}>
                  {humanize(r)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Scope" htmlFor="suppression-scope">
          <Select value={scope} onValueChange={(value) => setScope(value as SuppressionScope)}>
            <SelectTrigger id="suppression-scope">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SCOPES.map((s) => (
                <SelectItem key={s} value={s}>
                  {humanize(s)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Notes (optional)" htmlFor="suppression-notes">
          <Textarea id="suppression-notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </FormField>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
