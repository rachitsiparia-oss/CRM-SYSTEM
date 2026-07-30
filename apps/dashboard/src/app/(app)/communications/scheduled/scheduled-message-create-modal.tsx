"use client";

import { useState } from "react";
import type { ScheduledMessagePurpose } from "@rkpr/contracts";

import {
  useCommunicationChannels,
  useCreateScheduledMessage,
  useMessageTemplates,
} from "@/lib/hooks/use-communications";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { Modal } from "@/components/modals/modal";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const PURPOSES: ScheduledMessagePurpose[] = [
  "reservation_reminder",
  "feedback_request",
  "lead_follow_up",
  "manual",
];
const NO_TEMPLATE = "__none";

export function ScheduledMessageCreateModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: channels } = useCommunicationChannels();
  const { data: templates } = useMessageTemplates();
  const createScheduled = useCreateScheduledMessage();

  const [purpose, setPurpose] = useState<ScheduledMessagePurpose>("manual");
  const [channelId, setChannelId] = useState("");
  const [templateId, setTemplateId] = useState(NO_TEMPLATE);
  const [recipient, setRecipient] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setPurpose("manual");
    setChannelId("");
    setTemplateId(NO_TEMPLATE);
    setRecipient("");
    setScheduledFor("");
    setError(null);
  }

  async function handleSubmit() {
    setError(null);
    try {
      await createScheduled.mutateAsync({
        purpose,
        channel_id: channelId,
        template_id: templateId === NO_TEMPLATE ? null : templateId,
        recipient_reference: recipient,
        scheduled_for: new Date(scheduledFor).toISOString(),
        idempotency_key: crypto.randomUUID(),
      });
      reset();
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The message could not be scheduled.");
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
      title="Schedule a message"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!channelId || !recipient.trim() || !scheduledFor || createScheduled.isPending}
            onClick={() => void handleSubmit()}
          >
            {createScheduled.isPending ? "Scheduling…" : "Schedule"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <FormField label="Purpose" htmlFor="scheduled-purpose">
          <Select value={purpose} onValueChange={(value) => setPurpose(value as ScheduledMessagePurpose)}>
            <SelectTrigger id="scheduled-purpose">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PURPOSES.map((p) => (
                <SelectItem key={p} value={p}>
                  {humanize(p)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Channel" htmlFor="scheduled-channel">
          <Select value={channelId} onValueChange={setChannelId}>
            <SelectTrigger id="scheduled-channel">
              <SelectValue placeholder="Select a channel" />
            </SelectTrigger>
            <SelectContent>
              {(channels ?? []).map((channel) => (
                <SelectItem key={channel.id} value={channel.id}>
                  {channel.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Template (optional)" htmlFor="scheduled-template">
          <Select value={templateId} onValueChange={setTemplateId}>
            <SelectTrigger id="scheduled-template">
              <SelectValue placeholder="No template" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NO_TEMPLATE}>No template</SelectItem>
              {(templates ?? []).map((template) => (
                <SelectItem key={template.id} value={template.id}>
                  {template.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>
        <FormField label="Recipient (phone or email)" htmlFor="scheduled-recipient">
          <Input
            id="scheduled-recipient"
            value={recipient}
            onChange={(e) => setRecipient(e.target.value)}
          />
        </FormField>
        <FormField label="Scheduled for" htmlFor="scheduled-for">
          <Input
            id="scheduled-for"
            type="datetime-local"
            value={scheduledFor}
            onChange={(e) => setScheduledFor(e.target.value)}
          />
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
