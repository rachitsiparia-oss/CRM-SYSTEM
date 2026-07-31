"""Deterministic evaluation of a `RuleNode` tree against a resolved fact
dict. Pure function, no I/O — every fact must already be resolved by
`app.commercial_rules.facts` before calling in.
"""

from __future__ import annotations

from typing import Any

from app.commercial_rules.schema import RuleCondition, RuleEvaluationResult, RuleGroup, RuleNode


def _eval_operator(operator: str, actual: Any, expected: Any) -> bool:
    if operator == "eq":
        return bool(actual == expected)
    if operator == "neq":
        return bool(actual != expected)
    if operator == "gt":
        return actual is not None and actual > expected
    if operator == "gte":
        return actual is not None and actual >= expected
    if operator == "lt":
        return actual is not None and actual < expected
    if operator == "lte":
        return actual is not None and actual <= expected
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    if operator == "contains":
        return actual is not None and expected in actual
    if operator == "is_true":
        return bool(actual) is True
    if operator == "is_false":
        return bool(actual) is False
    raise ValueError(f"Unknown rule operator: {operator!r}")


def _eval_condition(condition: RuleCondition, facts: dict[str, Any]) -> tuple[bool | None, str]:
    """Returns (result, fact_name). `result` is None when the fact is
    absent from the supplied fact dict (e.g. an `order.*` fact evaluated
    outside an order context) — an unknown condition never raises and
    never silently passes; the caller decides how to treat "unknown"."""
    if condition.fact not in facts:
        return None, condition.fact
    actual = facts[condition.fact]
    return _eval_operator(condition.operator, actual, condition.value), condition.fact


def _eval_node(
    node: RuleNode, facts: dict[str, Any], matched: list[str], failed: list[str], unknown: list[str]
) -> bool:
    if isinstance(node, RuleCondition):
        result, fact_name = _eval_condition(node, facts)
        if result is None:
            unknown.append(fact_name)
            return False
        (matched if result else failed).append(fact_name)
        return result

    if isinstance(node, RuleGroup):
        results = [_eval_node(child, facts, matched, failed, unknown) for child in node.conditions]
        if node.logic == "all":
            return all(results)
        if node.logic == "any":
            return any(results)
        if node.logic == "not":
            return not any(results)
        raise ValueError(f"Unknown rule group logic: {node.logic!r}")

    raise TypeError(f"Unknown rule node type: {type(node)!r}")


def evaluate(node: RuleNode, facts: dict[str, Any]) -> RuleEvaluationResult:
    matched: list[str] = []
    failed: list[str] = []
    unknown: list[str] = []
    eligible = _eval_node(node, facts, matched, failed, unknown)
    return RuleEvaluationResult(
        eligible=eligible, matched_facts=matched, failed_facts=failed, unknown_facts=unknown
    )
