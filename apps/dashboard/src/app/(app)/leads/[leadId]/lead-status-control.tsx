"use client";

import { useState } from "react";
import type { Lead, LeadStatus, LostReason } from "@rkpr/contracts";

import { useTransitionLead } from "@/lib/hooks/use-leads";
import { humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
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

/** Mirrors app/leads/states.py::ALLOWED_TRANSITIONS so staff are only
 * offered moves the backend will accept. The backend re-validates every
 * transition regardless — this is usability, not enforcement
 * (ARCHITECTURE_AND_TECH_STACK.md section 6.9). `won` appears in no list:
 * it is reachable only through the conversion service. */
export const ALLOWED_TRANSITIONS: Record<LeadStatus, LeadStatus[]> = {
  new: ["contacted", "qualified", "lost", "closed"],
  contacted: ["qualified", "interested", "follow_up_scheduled", "lost", "closed"],
  qualified: ["interested", "follow_up_scheduled", "proposal_shared", "lost", "closed"],
  interested: ["follow_up_scheduled", "proposal_shared", "negotiating", "lost", "closed"],
  follow_up_scheduled: [
    "qualified",
    "interested",
    "proposal_shared",
    "negotiating",
    "lost",
    "closed",
  ],
  proposal_shared: ["negotiating", "lost", "closed"],
  negotiating: ["proposal_shared", "lost", "closed"],
  won: ["closed"],
  lost: ["new", "closed"],
  closed: [],
};

const LOST_REASONS: LostReason[] = [
  "budget",
  "timing",
  "no_response",
  "chose_competitor",
  "service_unavailable",
  "location_issue",
  "menu_mismatch",
  "duplicate",
  "invalid_enquiry",
];

const NONE = "__none";

export function LeadStatusControl({ lead }: { lead: Lead }) {
  const transitionLead = useTransitionLead(lead.id);
  const [newStatus, setNewStatus] = useState(NONE);
  const [lostReason, setLostReason] = useState<string>(LOST_REASONS[0]);
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const available = ALLOWED_TRANSITIONS[lead.status];

  if (available.length === 0) {
    return (
      <SectionCard title="Pipeline status">
        <p className="text-muted-foreground text-sm">
          This lead is {humanize(lead.status).toLowerCase()} — it has reached the end of the
          pipeline and cannot be moved further.
        </p>
      </SectionCard>
    );
  }

  async function handleTransition() {
    setError(null);
    try {
      await transitionLead.mutateAsync({
        newStatus,
        reason: reason.trim() || undefined,
        lostReason: newStatus === "lost" ? lostReason : undefined,
      });
      setNewStatus(NONE);
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The status could not be changed.");
    }
  }

  return (
    <SectionCard
      title="Pipeline status"
      description={`Currently ${humanize(lead.status).toLowerCase()}. Only valid next stages are listed.`}
    >
      <div className="flex flex-wrap items-end gap-4">
        <FormField label="Move to" htmlFor="lead-new-status" className="w-52">
          <Select value={newStatus} onValueChange={setNewStatus}>
            <SelectTrigger id="lead-new-status">
              <SelectValue placeholder="Select a stage" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={NONE}>Select a stage…</SelectItem>
              {available.map((status) => (
                <SelectItem key={status} value={status}>
                  {humanize(status)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        {newStatus === "lost" && (
          <FormField label="Lost reason" htmlFor="lead-lost-reason" required className="w-52">
            <Select value={lostReason} onValueChange={setLostReason}>
              <SelectTrigger id="lead-lost-reason">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LOST_REASONS.map((option) => (
                  <SelectItem key={option} value={option}>
                    {humanize(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        )}

        <FormField label="Note (optional)" htmlFor="lead-transition-reason" className="min-w-56 flex-1">
          <Input
            id="lead-transition-reason"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Why is it moving?"
          />
        </FormField>

        <Button
          className="mb-1"
          disabled={newStatus === NONE || transitionLead.isPending}
          onClick={() => void handleTransition()}
        >
          {transitionLead.isPending ? "Updating…" : "Update status"}
        </Button>
      </div>

      {error && (
        <p role="alert" className="text-destructive mt-3 text-sm">
          {error}
        </p>
      )}

      <p className="text-muted-foreground mt-3 text-xs">
        Marking a lead won happens through “Convert to customer”, so a customer record is always
        created alongside it.
      </p>
    </SectionCard>
  );
}
