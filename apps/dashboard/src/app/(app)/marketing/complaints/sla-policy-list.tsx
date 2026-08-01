"use client";

import { useState } from "react";
import type { SlaPolicy } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import { useCreateSlaPolicy, useSlaPolicyList, useUpdateSlaPolicy } from "@/lib/hooks/use-complaints";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface PolicyFormState {
  code: string;
  name: string;
  first_response_minutes: string;
  acknowledgement_minutes: string;
  resolution_minutes: string;
  follow_up_minutes: string;
  escalation_after_minutes: string;
  business_hours_only: boolean;
}

const EMPTY_FORM: PolicyFormState = {
  code: "",
  name: "",
  first_response_minutes: "60",
  acknowledgement_minutes: "120",
  resolution_minutes: "1440",
  follow_up_minutes: "",
  escalation_after_minutes: "",
  business_hours_only: true,
};

export function SlaPolicyList() {
  const { data: currentUser } = useCurrentUser();
  const { data: policies, isLoading } = useSlaPolicyList();
  const canManage = hasPermission(currentUser, "complaints.sla.manage");

  const [showCreate, setShowCreate] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<SlaPolicy | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end">
        {canManage && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="size-4" />
            New SLA policy
          </Button>
        )}
      </div>

      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : !policies || policies.length === 0 ? (
        <EmptyState
          title="No SLA policies configured"
          description="Complaints created without a matching policy have no SLA due dates."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {policies.map((policy) => (
            <SectionCard
              key={policy.id}
              title={policy.name}
              description={policy.code}
              actions={
                <div className="flex items-center gap-2">
                  <StatusBadge
                    label={policy.is_active ? "Active" : "Inactive"}
                    tone={policy.is_active ? "success" : "neutral"}
                  />
                  {canManage && (
                    <Button size="sm" variant="ghost" onClick={() => setEditingPolicy(policy)}>
                      Edit
                    </Button>
                  )}
                </div>
              }
            >
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted-foreground text-xs">First response</dt>
                  <dd>{policy.first_response_minutes} min</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground text-xs">Acknowledgement</dt>
                  <dd>{policy.acknowledgement_minutes} min</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground text-xs">Resolution</dt>
                  <dd>{policy.resolution_minutes} min</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground text-xs">Escalates after</dt>
                  <dd>{policy.escalation_after_minutes ?? "—"} min</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground text-xs">Business hours only</dt>
                  <dd>{policy.business_hours_only ? "Yes" : "No"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground text-xs">Applies to</dt>
                  <dd>
                    {policy.applicable_categories?.join(", ") ?? "Any category"} /{" "}
                    {policy.applicable_severities?.join(", ") ?? "Any severity"}
                  </dd>
                </div>
              </dl>
            </SectionCard>
          ))}
        </div>
      )}

      <SlaPolicyFormModal open={showCreate} onOpenChange={setShowCreate} />
      <SlaPolicyFormModal
        open={!!editingPolicy}
        onOpenChange={(open) => !open && setEditingPolicy(null)}
        policy={editingPolicy}
      />
    </div>
  );
}

function SlaPolicyFormModal({
  open,
  onOpenChange,
  policy,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  policy?: SlaPolicy | null;
}) {
  const isEdit = !!policy;
  const createPolicy = useCreateSlaPolicy();
  const updatePolicy = useUpdateSlaPolicy(policy?.id ?? "");
  const isPending = createPolicy.isPending || updatePolicy.isPending;

  const [form, setForm] = useState<PolicyFormState>(() =>
    policy
      ? {
          code: policy.code,
          name: policy.name,
          first_response_minutes: String(policy.first_response_minutes),
          acknowledgement_minutes: String(policy.acknowledgement_minutes),
          resolution_minutes: String(policy.resolution_minutes),
          follow_up_minutes: policy.follow_up_minutes ? String(policy.follow_up_minutes) : "",
          escalation_after_minutes: policy.escalation_after_minutes
            ? String(policy.escalation_after_minutes)
            : "",
          business_hours_only: policy.business_hours_only,
        }
      : EMPTY_FORM,
  );
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    form.name.trim() &&
    (isEdit || form.code.trim()) &&
    Number(form.first_response_minutes) > 0 &&
    Number(form.acknowledgement_minutes) > 0 &&
    Number(form.resolution_minutes) > 0 &&
    !isPending;

  return (
    <Modal
      open={open}
      onOpenChange={(next) => {
        if (!next) {
          setForm(EMPTY_FORM);
          setError(null);
        }
        onOpenChange(next);
      }}
      title={isEdit ? "Edit SLA policy" : "New SLA policy"}
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canSubmit}
            onClick={() => {
              setError(null);
              const payload = {
                name: form.name.trim(),
                first_response_minutes: Math.round(Number(form.first_response_minutes)),
                acknowledgement_minutes: Math.round(Number(form.acknowledgement_minutes)),
                resolution_minutes: Math.round(Number(form.resolution_minutes)),
                follow_up_minutes: form.follow_up_minutes.trim()
                  ? Math.round(Number(form.follow_up_minutes))
                  : null,
                escalation_after_minutes: form.escalation_after_minutes.trim()
                  ? Math.round(Number(form.escalation_after_minutes))
                  : null,
                business_hours_only: form.business_hours_only,
              };
              const onSettled = {
                onSuccess: () => onOpenChange(false),
                onError: (err: unknown) =>
                  setError(err instanceof ApiError ? err.message : "Could not save this policy."),
              };
              if (isEdit) {
                updatePolicy.mutate(payload, onSettled);
              } else {
                createPolicy.mutate({ ...payload, code: form.code.trim() }, onSettled);
              }
            }}
          >
            {isPending ? "Saving…" : isEdit ? "Save changes" : "Create policy"}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        {error && (
          <p role="alert" className="text-destructive text-sm">
            {error}
          </p>
        )}
        <div className="grid grid-cols-2 gap-3">
          {!isEdit && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="sla-code">Code</Label>
              <Input
                id="sla-code"
                value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
              />
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="sla-name">Name</Label>
            <Input
              id="sla-name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="sla-first-response">First response (min)</Label>
            <Input
              id="sla-first-response"
              type="number"
              min={1}
              value={form.first_response_minutes}
              onChange={(e) =>
                setForm((f) => ({ ...f, first_response_minutes: e.target.value }))
              }
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="sla-acknowledgement">Acknowledgement (min)</Label>
            <Input
              id="sla-acknowledgement"
              type="number"
              min={1}
              value={form.acknowledgement_minutes}
              onChange={(e) =>
                setForm((f) => ({ ...f, acknowledgement_minutes: e.target.value }))
              }
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="sla-resolution">Resolution (min)</Label>
            <Input
              id="sla-resolution"
              type="number"
              min={1}
              value={form.resolution_minutes}
              onChange={(e) => setForm((f) => ({ ...f, resolution_minutes: e.target.value }))}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="sla-follow-up">Follow-up (min, optional)</Label>
            <Input
              id="sla-follow-up"
              type="number"
              min={1}
              value={form.follow_up_minutes}
              onChange={(e) => setForm((f) => ({ ...f, follow_up_minutes: e.target.value }))}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="sla-escalation">Escalates after (min, optional)</Label>
            <Input
              id="sla-escalation"
              type="number"
              min={1}
              value={form.escalation_after_minutes}
              onChange={(e) =>
                setForm((f) => ({ ...f, escalation_after_minutes: e.target.value }))
              }
            />
          </div>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.business_hours_only}
            onChange={(e) => setForm((f) => ({ ...f, business_hours_only: e.target.checked }))}
          />
          Only count business hours toward due dates
        </label>
      </div>
    </Modal>
  );
}
