"""The constrained condition schema every rule-bearing entity (segments,
offer eligibility, achievement conditions) stores as its JSONB payload.

A rule is a tree of `RuleGroup` nodes (`all`/`any`/`not` logic) whose
leaves are `RuleCondition` nodes (`fact` + `operator` + `value`). `fact`
is restricted to `SUPPORTED_FACTS` below — there is no way to reference an
arbitrary column, table, or expression. This is the *only* place a rule
definition is accepted from a caller; every write path (segments, offers,
achievements) validates through `RuleNode` before persisting.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator

RuleOperator = Literal[
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
]

# The fixed, closed set of facts a condition may reference — every one
# resolved from real CRM data by app.commercial_rules.facts. Adding a new
# fact means adding a resolver function, never accepting a caller-supplied
# path.
SUPPORTED_FACTS: tuple[str, ...] = (
    "customer.created_at",
    "customer.days_since_created",
    "customer.lifetime_spend_minor",
    "customer.rolling_90d_spend_minor",
    "customer.completed_order_count",
    "customer.average_order_value_minor",
    "customer.days_since_last_order",
    "customer.visit_count",
    "customer.no_show_count",
    "customer.cancellation_count",
    "customer.loyalty_tier_rank",
    "customer.loyalty_points_balance",
    "customer.tags",
    "customer.segment_codes",
    "customer.whatsapp_consent",
    "customer.email_consent",
    "customer.sms_consent",
    "customer.birthday_month",
    "customer.referral_count",
    "customer.has_purchased_gift_card",
    # Order-context facts — only populated when evaluating against a
    # specific order (offer redemption at checkout); absent (None) during
    # segment/achievement evaluation, and any condition referencing one
    # then evaluates to a documented "unknown" failure, never a crash.
    "order.channel",
    "order.order_type",
    "order.subtotal_minor",
    "order.product_ids",
    "order.category_ids",
)


class RuleCondition(BaseModel):
    kind: Literal["condition"] = "condition"
    fact: str
    operator: RuleOperator
    value: Any = None

    @field_validator("fact")
    @classmethod
    def _fact_is_supported(cls, value: str) -> str:
        if value not in SUPPORTED_FACTS:
            raise ValueError(f"Unsupported rule fact: {value!r}")
        return value


class RuleGroup(BaseModel):
    kind: Literal["group"] = "group"
    logic: Literal["all", "any", "not"]
    conditions: list[RuleNode] = Field(min_length=1)


RuleNode = Annotated[RuleCondition | RuleGroup, Field(discriminator="kind")]
RuleGroup.model_rebuild()


class RuleEvaluationResult(BaseModel):
    """GROWTH_AND_INTELLIGENCE.md's own requirement: "Evaluation results
    must be explainable." Returned by every evaluate_* call in
    `app.commercial_rules.evaluator`."""

    eligible: bool
    matched_facts: list[str]
    failed_facts: list[str]
    unknown_facts: list[str]
