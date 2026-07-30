"use client";

import { useState } from "react";
import type { Conversation } from "@rkpr/contracts";

import {
  useAddInternalNote,
  useMessageTemplates,
  useReplyToConversation,
} from "@/lib/hooks/use-communications";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const NO_TEMPLATE = "__none";

export function ConversationComposer({ conversation }: { conversation: Conversation }) {
  const { data: currentUser } = useCurrentUser();
  const canReply = hasPermission(currentUser, "communications.reply");
  const canAddNote = hasPermission(currentUser, "communications.notes.create");

  const [mode, setMode] = useState<"reply" | "note">(canReply ? "reply" : "note");
  const [body, setBody] = useState("");
  const [templateId, setTemplateId] = useState(NO_TEMPLATE);
  const [error, setError] = useState<string | null>(null);

  const { data: templates } = useMessageTemplates({ channelId: conversation.channel_id });
  const reply = useReplyToConversation(conversation.id);
  const addNote = useAddInternalNote(conversation.id);

  if (!canReply && !canAddNote) return null;

  async function handleSend() {
    setError(null);
    try {
      if (mode === "reply") {
        await reply.mutateAsync({
          body_text: templateId === NO_TEMPLATE ? body.trim() : undefined,
          template_id: templateId === NO_TEMPLATE ? undefined : templateId,
          idempotency_key: crypto.randomUUID(),
        });
      } else {
        await addNote.mutateAsync({ body_text: body.trim() });
      }
      setBody("");
      setTemplateId(NO_TEMPLATE);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The message could not be sent.");
    }
  }

  const isPending = reply.isPending || addNote.isPending;
  const canSend = mode === "reply" ? (templateId !== NO_TEMPLATE || !!body.trim()) : !!body.trim();

  return (
    <SectionCard title="Reply">
      <div className="mb-3 flex gap-2">
        {canReply && (
          <Button
            type="button"
            size="sm"
            variant={mode === "reply" ? "default" : "outline"}
            onClick={() => setMode("reply")}
          >
            Reply to customer
          </Button>
        )}
        {canAddNote && (
          <Button
            type="button"
            size="sm"
            variant={mode === "note" ? "default" : "outline"}
            onClick={() => setMode("note")}
          >
            Internal note
          </Button>
        )}
      </div>

      {mode === "reply" && (
        <FormField label="Template (optional)" htmlFor="composer-template" className="mb-3">
          <Select value={templateId} onValueChange={setTemplateId}>
            <SelectTrigger id="composer-template">
              <SelectValue placeholder="No template — freeform message" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NO_TEMPLATE}>No template — freeform message</SelectItem>
              {(templates ?? [])
                .filter((template) => template.status === "active")
                .map((template) => (
                  <SelectItem key={template.id} value={template.id}>
                    {template.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </FormField>
      )}

      {(mode === "note" || templateId === NO_TEMPLATE) && (
        <FormField
          label={mode === "reply" ? "Message" : "Note"}
          htmlFor="composer-body"
          className="mb-3"
        >
          <Textarea
            id="composer-body"
            rows={4}
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder={
              mode === "reply" ? "Type your reply…" : "Visible only to staff, never sent to the customer."
            }
          />
        </FormField>
      )}

      <div className="flex justify-end">
        <Button disabled={!canSend || isPending} onClick={() => void handleSend()}>
          {isPending ? "Sending…" : mode === "reply" ? "Send reply" : "Add note"}
        </Button>
      </div>

      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}
    </SectionCard>
  );
}
