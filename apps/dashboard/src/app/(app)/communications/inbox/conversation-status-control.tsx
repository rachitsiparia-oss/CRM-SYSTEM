"use client";

import { useState } from "react";
import type { Conversation, ConversationStatus } from "@rkpr/contracts";

import { useTransitionConversation } from "@/lib/hooks/use-communications";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { FormField } from "@/components/forms/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

/** Mirrors app.communications.states.CONVERSATION_TRANSITIONS so staff are
 * only offered moves the backend will accept — the backend re-validates
 * every transition regardless. */
const TRANSITIONS: Record<ConversationStatus, ConversationStatus[]> = {
  open: ["pending", "waiting_on_customer", "waiting_on_staff", "snoozed", "resolved", "spam"],
  pending: ["open", "waiting_on_customer", "waiting_on_staff", "snoozed", "resolved", "spam"],
  waiting_on_customer: ["waiting_on_staff", "open", "resolved", "snoozed", "spam"],
  waiting_on_staff: ["waiting_on_customer", "open", "resolved", "snoozed", "spam"],
  snoozed: ["open", "waiting_on_customer", "waiting_on_staff", "resolved"],
  resolved: ["open", "closed"],
  closed: ["open"],
  spam: ["open", "closed"],
};

export function ConversationStatusControl({ conversation }: { conversation: Conversation }) {
  const { data: currentUser } = useCurrentUser();
  const transition = useTransitionConversation(conversation.id);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const available = TRANSITIONS[conversation.status];
  const canResolve = hasPermission(currentUser, "communications.resolve");
  const canReopen = hasPermission(currentUser, "communications.reopen");
  const canSnooze = hasPermission(currentUser, "communications.snooze");

  function isAllowed(target: ConversationStatus): boolean {
    if (target === "resolved" || target === "closed") return canResolve;
    if (target === "open" && ["resolved", "closed", "spam"].includes(conversation.status)) {
      return canReopen;
    }
    if (target === "snoozed") return canSnooze;
    return true;
  }

  async function applyTransition(target: ConversationStatus) {
    setError(null);
    try {
      await transition.mutateAsync({ target_status: target, reason: reason.trim() || undefined });
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The status could not be changed.");
    }
  }

  const offered = available.filter(isAllowed);
  if (offered.length === 0) {
    return (
      <SectionCard title="Conversation status">
        <p className="text-muted-foreground text-sm">
          Currently {humanize(conversation.status).toLowerCase()}. No further status changes are
          available to you.
        </p>
      </SectionCard>
    );
  }

  return (
    <SectionCard
      title="Conversation status"
      description={`Currently ${humanize(conversation.status).toLowerCase()}.`}
    >
      <div className="flex flex-wrap items-end gap-3">
        <FormField label="Note (optional)" htmlFor="conversation-transition-reason" className="min-w-56 flex-1">
          <Input
            id="conversation-transition-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </FormField>
        {offered.map((target) => (
          <Button
            key={target}
            variant={target === "spam" ? "destructive" : "default"}
            disabled={transition.isPending}
            onClick={() => void applyTransition(target)}
          >
            {humanize(target)}
          </Button>
        ))}
      </div>
      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}
    </SectionCard>
  );
}
