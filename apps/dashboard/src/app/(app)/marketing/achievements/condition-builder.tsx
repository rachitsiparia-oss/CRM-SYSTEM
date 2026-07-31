"use client";

import type { CommercialRuleFact, RuleCondition, RuleNode, RuleOperator } from "@rkpr/contracts";
import { COMMERCIAL_RULE_FACTS } from "@rkpr/contracts";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export const RULE_OPERATORS: RuleOperator[] = [
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

const OPERATOR_LABELS: Record<RuleOperator, string> = {
  eq: "equals",
  neq: "does not equal",
  gt: "is greater than",
  gte: "is at least",
  lt: "is less than",
  lte: "is at most",
  in: "is one of",
  not_in: "is not one of",
  contains: "contains",
  is_true: "is true",
  is_false: "is false",
};

/** Achievement conditions use the same closed rule tree as Segments/Offers
 * (packages/contracts `RuleNode`), but this builder only ever produces a
 * single leaf `RuleCondition` — the task scope for achievement authoring
 * is a nested-tree-free "when this one fact crosses this threshold" rule,
 * per the explicit instruction not to build a nested tree editor here. */
export function coercePrimitive(raw: string): unknown {
  const trimmed = raw.trim();
  if (trimmed === "") return trimmed;
  if (trimmed === "true") return true;
  if (trimmed === "false") return false;
  const asNumber = Number(trimmed);
  if (!Number.isNaN(asNumber)) return asNumber;
  return trimmed;
}

export function buildConditionValue(operator: RuleOperator, raw: string): unknown {
  if (operator === "is_true") return true;
  if (operator === "is_false") return false;
  if (operator === "in" || operator === "not_in") {
    return raw
      .split(",")
      .map((part) => part.trim())
      .filter((part) => part.length > 0)
      .map(coercePrimitive);
  }
  return coercePrimitive(raw);
}

export function valueToInputText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

export interface SingleConditionBuilderProps {
  fact: CommercialRuleFact;
  operator: RuleOperator;
  valueText: string;
  onFactChange: (fact: CommercialRuleFact) => void;
  onOperatorChange: (operator: RuleOperator) => void;
  onValueTextChange: (value: string) => void;
  disabled?: boolean;
}

export function SingleConditionBuilder({
  fact,
  operator,
  valueText,
  onFactChange,
  onOperatorChange,
  onValueTextChange,
  disabled,
}: SingleConditionBuilderProps) {
  const needsValue = operator !== "is_true" && operator !== "is_false";

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <div className="flex flex-col gap-1.5">
        <Label>Fact</Label>
        <Select value={fact} onValueChange={(v) => onFactChange(v as CommercialRuleFact)} disabled={disabled}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {COMMERCIAL_RULE_FACTS.map((f) => (
              <SelectItem key={f} value={f}>
                {f}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label>Operator</Label>
        <Select
          value={operator}
          onValueChange={(v) => onOperatorChange(v as RuleOperator)}
          disabled={disabled}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {RULE_OPERATORS.map((op) => (
              <SelectItem key={op} value={op}>
                {OPERATOR_LABELS[op]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="condition-value">Value</Label>
        <Input
          id="condition-value"
          disabled={disabled || !needsValue}
          placeholder={
            operator === "in" || operator === "not_in" ? "Comma-separated values" : "Value"
          }
          value={needsValue ? valueText : ""}
          onChange={(e) => onValueTextChange(e.target.value)}
        />
      </div>
    </div>
  );
}

/** Read-only, human-readable summary of any RuleNode — including nested
 * groups the API or seed data may have produced even though this UI only
 * authors single conditions. */
export function summarizeRuleNode(node: RuleNode): string {
  if (node.kind === "condition") {
    const condition = node as RuleCondition;
    const label = OPERATOR_LABELS[condition.operator] ?? condition.operator;
    if (condition.operator === "is_true" || condition.operator === "is_false") {
      return `${condition.fact} ${label}`;
    }
    return `${condition.fact} ${label} ${valueToInputText(condition.value)}`;
  }
  const joiner = node.logic === "all" ? " AND " : node.logic === "any" ? " OR " : " NOT ";
  const parts = node.conditions.map(summarizeRuleNode);
  return node.logic === "not" ? `NOT (${parts.join(", ")})` : `(${parts.join(joiner)})`;
}

export function isSingleCondition(node: RuleNode): node is RuleCondition {
  return node.kind === "condition";
}
