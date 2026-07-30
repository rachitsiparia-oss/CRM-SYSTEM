"use client";

import { useState } from "react";
import type { CallDirection, CallOutcome } from "@rkpr/contracts";

import { useCreateCallLog } from "@/lib/hooks/use-communications";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const DIRECTIONS: CallDirection[] = ["inbound", "outbound"];
const OUTCOMES: CallOutcome[] = ["connected", "no_answer", "voicemail", "busy", "wrong_number", "other"];

export function CallLogCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createCallLog = useCreateCallLog();
  const [direction, setDirection] = useState<CallDirection>("outbound");
  const [outcome, setOutcome] = useState<CallOutcome>("connected");
  const [startedAt, setStartedAt] = useState("");
  const [notes, setNotes] = useState("");
  const [followUpRequired, setFollowUpRequired] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setDirection("outbound");
    setOutcome("connected");
    setStartedAt("");
    setNotes("");
    setFollowUpRequired(false);
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    try {
      await createCallLog.mutateAsync({
        direction,
        outcome,
        started_at: new Date(startedAt).toISOString(),
        notes: notes.trim() || null,
        follow_up_required: followUpRequired,
      });
      reset();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The call log could not be saved.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Log a call"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!startedAt || createCallLog.isPending} onClick={() => void handleSubmit()}>
            {createCallLog.isPending ? "Saving…" : "Save call log"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <FormField label="Direction" htmlFor="call-direction">
          <Select value={direction} onValueChange={(value) => setDirection(value as CallDirection)}>
            <SelectTrigger id="call-direction">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {DIRECTIONS.map((d) => (
                <SelectItem key={d} value={d}>
                  {humanize(d)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Started at" htmlFor="call-started-at">
          <Input
            id="call-started-at"
            type="datetime-local"
            value={startedAt}
            onChange={(e) => setStartedAt(e.target.value)}
          />
        </FormField>
        <FormField label="Outcome" htmlFor="call-outcome">
          <Select value={outcome} onValueChange={(value) => setOutcome(value as CallOutcome)}>
            <SelectTrigger id="call-outcome">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {OUTCOMES.map((o) => (
                <SelectItem key={o} value={o}>
                  {humanize(o)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Notes" htmlFor="call-notes">
          <Textarea id="call-notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </FormField>
        <label className="flex items-center gap-2 text-sm">
          <Checkbox
            checked={followUpRequired}
            onCheckedChange={(checked) => setFollowUpRequired(checked === true)}
          />
          Follow-up required
        </label>
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
      </div>
    </Modal>
  );
}
