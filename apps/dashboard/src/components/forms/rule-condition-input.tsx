"use client";

import type { CommercialRuleFact, RuleCondition, RuleOperator } from "@rkpr/contracts";
import { COMMERCIAL_RULE_FACTS } from "@rkpr/contracts";

import { humanize } from "@/lib/crm-display";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const OPERATORS: RuleOperator[] = [
  "eq",
  "neq",
  "gt",
  "gte",
  "lt",
  "lte",
  "in",
  "not_in",
  "contains",
  "is_true",
  "is_false",
];

/** The draft (string-valued) form of a single `RuleCondition` — kept as
 * raw text while editing so the value input never fights the user's
 * keystrokes, then coerced to the typed `unknown` the API expects only at
 * submit time via `buildRuleCondition`. */
export interface RuleConditionDraft {
  fact: CommercialRuleFact;
  operator: RuleOperator;
  value: string;
}

export const DEFAULT_RULE_CONDITION_DRAFT: RuleConditionDraft = {
  fact: COMMERCIAL_RULE_FACTS[0],
  operator: "gte",
  value: "0",
};

function coerceScalar(raw: string): unknown {
  if (raw === "") return raw;
  if (raw === "true") return true;
  if (raw === "false") return false;
  const num = Number(raw);
  if (!Number.isNaN(num)) return num;
  return raw;
}

function coerceValue(operator: RuleOperator, raw: string): unknown {
  if (operator === "is_true" || operator === "is_false") return null;
  const trimmed = raw.trim();
  if (operator === "in" || operator === "not_in") {
    return trimmed
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)
      .map(coerceScalar);
  }
  return coerceScalar(trimmed);
}

/** Builds the `RuleCondition` the API contract requires (CommercialRuleFact
 * + RuleOperator + coerced value) from the plain-text draft this input
 * collects — the single-condition rule builder scope explicitly called for
 * in place of a full nested AND/OR tree editor. */
export function buildRuleCondition(draft: RuleConditionDraft): RuleCondition {
  return {
    kind: "condition",
    fact: draft.fact,
    operator: draft.operator,
    value: coerceValue(draft.operator, draft.value),
  };
}

export interface RuleConditionInputProps {
  draft: RuleConditionDraft;
  onChange: (next: RuleConditionDraft) => void;
  disabled?: boolean;
}

/** A single fact/operator/value row for the shared commercial-rules
 * condition schema (Segments' `rule_definition`, Offers' `eligibility_rule`).
 * Intentionally does not build a nested all/any/not tree — GROWTH_AND_INTELLIGENCE
 * scope for these two modules' create forms is one condition. */
export function RuleConditionInput({ draft, onChange, disabled }: RuleConditionInputProps) {
  const needsValue = draft.operator !== "is_true" && draft.operator !== "is_false";

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div className="flex flex-col gap-1.5">
        <Label>Fact</Label>
        <Select
          value={draft.fact}
          onValueChange={(next) => onChange({ ...draft, fact: next as CommercialRuleFact })}
          disabled={disabled}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {COMMERCIAL_RULE_FACTS.map((fact) => (
              <SelectItem key={fact} value={fact}>
                {fact}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Operator</Label>
        <Select
          value={draft.operator}
          onValueChange={(next) => onChange({ ...draft, operator: next as RuleOperator })}
          disabled={disabled}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {OPERATORS.map((operator) => (
              <SelectItem key={operator} value={operator}>
                {humanize(operator)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Value</Label>
        <Input
          value={draft.value}
          disabled={disabled || !needsValue}
          placeholder={
            !needsValue
              ? "Not required"
              : draft.operator === "in" || draft.operator === "not_in"
                ? "comma,separated,values"
                : "value"
          }
          onChange={(e) => onChange({ ...draft, value: e.target.value })}
        />
      </div>
    </div>
  );
}
