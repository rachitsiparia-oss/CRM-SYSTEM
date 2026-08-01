"use client";

import { useState } from "react";
import type { ApprovalRule, RecoveryType } from "@rkpr/contracts";
import { Plus } from "lucide-react";

import {
  useApprovalRuleList,
  useCreateApprovalRule,
  useUpdateApprovalRule,
} from "@/lib/hooks/use-service-recovery";
import { hasPermission, useCurrentUser } from "@/lib/hooks/use-current-user";
import { formatMinorUnits, humanize } from "@/lib/crm-display";
import { ApiError } from "@/lib/api/errors";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { Modal } from "@/components/modals/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CurrencyInput } from "@/components/forms/currency-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const RECOVERY_TYPES: RecoveryType[] = [
  "apology_only",
  "replacement",
  "refund_request",
  "approved_refund",
  "discount",
  "coupon",
  "loyalty_credit",
  "complimentary_item",
  "manager_follow_up",
  "operational_correction",
];
const ANY_TYPE = "__any";

interface RuleFormState {
  code: string;
  name: string;
  recoveryType: string;
  minValue: string;
  maxValue: string;
  requiredPermission: string;
  allowSelfApproval: boolean;
}

const EMPTY_FORM: RuleFormState = {
  code: "",
  name: "",
  recoveryType: ANY_TYPE,
  minValue: "",
  maxValue: "",
  requiredPermission: "recovery.approve",
  allowSelfApproval: false,
};

export function ApprovalRuleList() {
  const { data: currentUser } = useCurrentUser();
  const { data: rules, isLoading } = useApprovalRuleList();
  const canManage = hasPermission(currentUser, "recovery.rules.manage");

  const [showCreate, setShowCreate] = useState(false);
  const [editingRule, setEditingRule] = useState<ApprovalRule | null>(null);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end">
        {canManage && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="size-4" />
            New approval rule
          </Button>
        )}
      </div>

      {isLoading ? (
        <p className="text-muted-foreground text-sm">Loading…</p>
      ) : !rules || rules.length === 0 ? (
        <EmptyState
          title="No approval rules configured"
          description="Every proposed recovery action is self-service until a matching rule requires approval."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {rules.map((rule) => (
            <SectionCard
              key={rule.id}
              title={rule.name}
              description={rule.code}
              actions={
                <div className="flex items-center gap-2">
                  <StatusBadge
                    label={rule.is_active ? "Active" : "Inactive"}
                    tone={rule.is_active ? "success" : "neutral"}
                  />
                  {canManage && (
                    <Button size="sm" variant="ghost" onClick={() => setEditingRule(rule)}>
                      Edit
                    </Button>
                  )}
                </div>
              }
            >
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted-foreground text-xs">Recovery type</dt>
                  <dd>{rule.recovery_type ? humanize(rule.recovery_type) : "Any"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground text-xs">Value range</dt>
                  <dd>
                    {rule.min_value_minor !== null ? formatMinorUnits(rule.min_value_minor) : "Any"}
                    {" – "}
                    {rule.max_value_minor !== null ? formatMinorUnits(rule.max_value_minor) : "Any"}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground text-xs">Required permission</dt>
                  <dd>{rule.required_permission}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground text-xs">Self-approval</dt>
                  <dd>{rule.allow_self_approval ? "Allowed" : "Not allowed"}</dd>
                </div>
              </dl>
            </SectionCard>
          ))}
        </div>
      )}

      <ApprovalRuleFormModal open={showCreate} onOpenChange={setShowCreate} />
      <ApprovalRuleFormModal
        open={!!editingRule}
        onOpenChange={(open) => !open && setEditingRule(null)}
        rule={editingRule}
      />
    </div>
  );
}

function ApprovalRuleFormModal({
  open,
  onOpenChange,
  rule,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  rule?: ApprovalRule | null;
}) {
  const isEdit = !!rule;
  const createRule = useCreateApprovalRule();
  const updateRule = useUpdateApprovalRule(rule?.id ?? "");
  const isPending = createRule.isPending || updateRule.isPending;

  const [form, setForm] = useState<RuleFormState>(() =>
    rule
      ? {
          code: rule.code,
          name: rule.name,
          recoveryType: rule.recovery_type ?? ANY_TYPE,
          minValue: rule.min_value_minor !== null ? String(rule.min_value_minor / 100) : "",
          maxValue: rule.max_value_minor !== null ? String(rule.max_value_minor / 100) : "",
          requiredPermission: rule.required_permission,
          allowSelfApproval: rule.allow_self_approval,
        }
      : EMPTY_FORM,
  );
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    form.name.trim() && (isEdit || form.code.trim()) && form.requiredPermission.trim() && !isPending;

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
      title={isEdit ? "Edit approval rule" : "New approval rule"}
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
                recovery_type:
                  form.recoveryType === ANY_TYPE ? null : (form.recoveryType as RecoveryType),
                min_value_minor: form.minValue.trim()
                  ? Math.round(Number(form.minValue) * 100)
                  : null,
                max_value_minor: form.maxValue.trim()
                  ? Math.round(Number(form.maxValue) * 100)
                  : null,
                required_permission: form.requiredPermission.trim(),
                allow_self_approval: form.allowSelfApproval,
              };
              const onSettled = {
                onSuccess: () => onOpenChange(false),
                onError: (err: unknown) =>
                  setError(err instanceof ApiError ? err.message : "Could not save this rule."),
              };
              if (isEdit) {
                updateRule.mutate(payload, onSettled);
              } else {
                createRule.mutate({ ...payload, code: form.code.trim() }, onSettled);
              }
            }}
          >
            {isPending ? "Saving…" : isEdit ? "Save changes" : "Create rule"}
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
              <Label htmlFor="rule-code">Code</Label>
              <Input
                id="rule-code"
                value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
              />
            </div>
          )}
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-name">Name</Label>
            <Input
              id="rule-name"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label>Recovery type</Label>
          <Select
            value={form.recoveryType}
            onValueChange={(v) => setForm((f) => ({ ...f, recoveryType: v }))}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ANY_TYPE}>Any type</SelectItem>
              {RECOVERY_TYPES.map((value) => (
                <SelectItem key={value} value={value}>
                  {humanize(value)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-min-value">Minimum value (optional)</Label>
            <CurrencyInput
              id="rule-min-value"
              value={form.minValue}
              onChange={(e) => setForm((f) => ({ ...f, minValue: e.target.value }))}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="rule-max-value">Maximum value (optional)</Label>
            <CurrencyInput
              id="rule-max-value"
              value={form.maxValue}
              onChange={(e) => setForm((f) => ({ ...f, maxValue: e.target.value }))}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="rule-permission">Required permission</Label>
          <Input
            id="rule-permission"
            value={form.requiredPermission}
            onChange={(e) => setForm((f) => ({ ...f, requiredPermission: e.target.value }))}
          />
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.allowSelfApproval}
            onChange={(e) => setForm((f) => ({ ...f, allowSelfApproval: e.target.checked }))}
          />
          Allow the proposer to approve their own action
        </label>
      </div>
    </Modal>
  );
}
