"""Pure unit tests of `app.commercial_rules.evaluator.evaluate()` — the
constrained rule engine shared by segments, offers, and achievements.

`evaluate()` is a synchronous, side-effect-free function over a hand-built
fact dict; no database is needed here. Every operator gets a
matching/not-matching case, group logic (`all`/`any`/`not`) is exercised
with multiple conditions, and the "unknown fact" contract (a fact absent
from the supplied dict never crashes and never silently passes) is
asserted precisely against `RuleEvaluationResult`.
"""

from __future__ import annotations

from app.commercial_rules.evaluator import evaluate
from app.commercial_rules.schema import RuleCondition, RuleGroup

# --- Individual operators ----------------------------------------------------


def test_eq_matches() -> None:
    node = RuleCondition(fact="order.channel", operator="eq", value="dine_in")
    result = evaluate(node, {"order.channel": "dine_in"})
    assert result.eligible is True
    assert result.matched_facts == ["order.channel"]
    assert result.failed_facts == []
    assert result.unknown_facts == []


def test_eq_does_not_match() -> None:
    node = RuleCondition(fact="order.channel", operator="eq", value="dine_in")
    result = evaluate(node, {"order.channel": "delivery"})
    assert result.eligible is False
    assert result.failed_facts == ["order.channel"]
    assert result.matched_facts == []


def test_neq_matches() -> None:
    node = RuleCondition(fact="order.channel", operator="neq", value="dine_in")
    result = evaluate(node, {"order.channel": "delivery"})
    assert result.eligible is True


def test_neq_does_not_match() -> None:
    node = RuleCondition(fact="order.channel", operator="neq", value="dine_in")
    result = evaluate(node, {"order.channel": "dine_in"})
    assert result.eligible is False


def test_gt_matches() -> None:
    node = RuleCondition(fact="customer.completed_order_count", operator="gt", value=5)
    result = evaluate(node, {"customer.completed_order_count": 6})
    assert result.eligible is True


def test_gt_does_not_match_when_equal() -> None:
    node = RuleCondition(fact="customer.completed_order_count", operator="gt", value=5)
    result = evaluate(node, {"customer.completed_order_count": 5})
    assert result.eligible is False


def test_gte_matches_when_equal() -> None:
    node = RuleCondition(fact="customer.completed_order_count", operator="gte", value=5)
    result = evaluate(node, {"customer.completed_order_count": 5})
    assert result.eligible is True


def test_gte_does_not_match() -> None:
    node = RuleCondition(fact="customer.completed_order_count", operator="gte", value=5)
    result = evaluate(node, {"customer.completed_order_count": 4})
    assert result.eligible is False


def test_lt_matches() -> None:
    node = RuleCondition(fact="customer.days_since_last_order", operator="lt", value=30)
    result = evaluate(node, {"customer.days_since_last_order": 10})
    assert result.eligible is True


def test_lt_does_not_match_when_equal() -> None:
    node = RuleCondition(fact="customer.days_since_last_order", operator="lt", value=30)
    result = evaluate(node, {"customer.days_since_last_order": 30})
    assert result.eligible is False


def test_lte_matches_when_equal() -> None:
    node = RuleCondition(fact="customer.days_since_last_order", operator="lte", value=30)
    result = evaluate(node, {"customer.days_since_last_order": 30})
    assert result.eligible is True


def test_lte_does_not_match() -> None:
    node = RuleCondition(fact="customer.days_since_last_order", operator="lte", value=30)
    result = evaluate(node, {"customer.days_since_last_order": 31})
    assert result.eligible is False


def test_in_matches() -> None:
    node = RuleCondition(fact="order.order_type", operator="in", value=["dine_in", "takeaway"])
    result = evaluate(node, {"order.order_type": "takeaway"})
    assert result.eligible is True


def test_in_does_not_match() -> None:
    node = RuleCondition(fact="order.order_type", operator="in", value=["dine_in", "takeaway"])
    result = evaluate(node, {"order.order_type": "delivery"})
    assert result.eligible is False


def test_not_in_matches() -> None:
    node = RuleCondition(fact="order.order_type", operator="not_in", value=["dine_in"])
    result = evaluate(node, {"order.order_type": "delivery"})
    assert result.eligible is True


def test_not_in_does_not_match() -> None:
    node = RuleCondition(fact="order.order_type", operator="not_in", value=["dine_in"])
    result = evaluate(node, {"order.order_type": "dine_in"})
    assert result.eligible is False


def test_contains_matches() -> None:
    node = RuleCondition(fact="customer.tags", operator="contains", value="vip")
    result = evaluate(node, {"customer.tags": ["vip", "regular"]})
    assert result.eligible is True


def test_contains_does_not_match() -> None:
    node = RuleCondition(fact="customer.tags", operator="contains", value="vip")
    result = evaluate(node, {"customer.tags": ["regular"]})
    assert result.eligible is False


def test_is_true_matches() -> None:
    node = RuleCondition(fact="customer.whatsapp_consent", operator="is_true")
    result = evaluate(node, {"customer.whatsapp_consent": True})
    assert result.eligible is True


def test_is_true_does_not_match() -> None:
    node = RuleCondition(fact="customer.whatsapp_consent", operator="is_true")
    result = evaluate(node, {"customer.whatsapp_consent": False})
    assert result.eligible is False


def test_is_false_matches() -> None:
    node = RuleCondition(fact="customer.whatsapp_consent", operator="is_false")
    result = evaluate(node, {"customer.whatsapp_consent": False})
    assert result.eligible is True


def test_is_false_does_not_match() -> None:
    node = RuleCondition(fact="customer.whatsapp_consent", operator="is_false")
    result = evaluate(node, {"customer.whatsapp_consent": True})
    assert result.eligible is False


# --- gt/gte/lt/lte against a None actual never raise -------------------------


def test_gt_against_none_actual_fails_without_raising() -> None:
    node = RuleCondition(fact="customer.days_since_last_order", operator="gt", value=5)
    result = evaluate(node, {"customer.days_since_last_order": None})
    assert result.eligible is False
    assert result.failed_facts == ["customer.days_since_last_order"]


# --- Group logic: all / any / not --------------------------------------------


def test_all_group_requires_every_condition() -> None:
    node = RuleGroup(
        logic="all",
        conditions=[
            RuleCondition(fact="customer.completed_order_count", operator="gte", value=3),
            RuleCondition(fact="customer.whatsapp_consent", operator="is_true"),
        ],
    )
    facts = {"customer.completed_order_count": 5, "customer.whatsapp_consent": True}
    result = evaluate(node, facts)
    assert result.eligible is True
    assert sorted(result.matched_facts) == [
        "customer.completed_order_count",
        "customer.whatsapp_consent",
    ]


def test_all_group_fails_if_one_condition_fails() -> None:
    node = RuleGroup(
        logic="all",
        conditions=[
            RuleCondition(fact="customer.completed_order_count", operator="gte", value=3),
            RuleCondition(fact="customer.whatsapp_consent", operator="is_true"),
        ],
    )
    facts = {"customer.completed_order_count": 5, "customer.whatsapp_consent": False}
    result = evaluate(node, facts)
    assert result.eligible is False
    assert result.matched_facts == ["customer.completed_order_count"]
    assert result.failed_facts == ["customer.whatsapp_consent"]


def test_any_group_passes_with_one_match() -> None:
    node = RuleGroup(
        logic="any",
        conditions=[
            RuleCondition(fact="customer.completed_order_count", operator="gte", value=100),
            RuleCondition(fact="customer.whatsapp_consent", operator="is_true"),
        ],
    )
    facts = {"customer.completed_order_count": 1, "customer.whatsapp_consent": True}
    result = evaluate(node, facts)
    assert result.eligible is True
    assert result.matched_facts == ["customer.whatsapp_consent"]
    assert result.failed_facts == ["customer.completed_order_count"]


def test_any_group_fails_when_all_fail() -> None:
    node = RuleGroup(
        logic="any",
        conditions=[
            RuleCondition(fact="customer.completed_order_count", operator="gte", value=100),
            RuleCondition(fact="customer.whatsapp_consent", operator="is_true"),
        ],
    )
    facts = {"customer.completed_order_count": 1, "customer.whatsapp_consent": False}
    result = evaluate(node, facts)
    assert result.eligible is False


def test_not_group_inverts_a_matching_condition() -> None:
    node = RuleGroup(
        logic="not",
        conditions=[RuleCondition(fact="customer.whatsapp_consent", operator="is_true")],
    )
    result = evaluate(node, {"customer.whatsapp_consent": True})
    assert result.eligible is False


def test_not_group_inverts_a_failing_condition() -> None:
    node = RuleGroup(
        logic="not",
        conditions=[RuleCondition(fact="customer.whatsapp_consent", operator="is_true")],
    )
    result = evaluate(node, {"customer.whatsapp_consent": False})
    assert result.eligible is True


def test_nested_groups_combine_correctly() -> None:
    # (completed_order_count >= 3 AND whatsapp_consent) OR vip tag present.
    node = RuleGroup(
        logic="any",
        conditions=[
            RuleGroup(
                logic="all",
                conditions=[
                    RuleCondition(fact="customer.completed_order_count", operator="gte", value=3),
                    RuleCondition(fact="customer.whatsapp_consent", operator="is_true"),
                ],
            ),
            RuleCondition(fact="customer.tags", operator="contains", value="vip"),
        ],
    )
    facts = {
        "customer.completed_order_count": 0,
        "customer.whatsapp_consent": False,
        "customer.tags": ["vip"],
    }
    result = evaluate(node, facts)
    assert result.eligible is True


# --- Unknown-fact contract -----------------------------------------------


def test_missing_fact_is_unknown_not_a_crash_and_not_a_silent_pass() -> None:
    node = RuleCondition(fact="order.subtotal_minor", operator="gte", value=10000)
    result = evaluate(node, {})  # order.* facts absent outside an order context
    assert result.eligible is False
    assert result.matched_facts == []
    assert result.failed_facts == []
    assert result.unknown_facts == ["order.subtotal_minor"]


def test_all_group_with_unknown_fact_is_ineligible() -> None:
    node = RuleGroup(
        logic="all",
        conditions=[
            RuleCondition(fact="customer.whatsapp_consent", operator="is_true"),
            RuleCondition(fact="order.subtotal_minor", operator="gte", value=10000),
        ],
    )
    result = evaluate(node, {"customer.whatsapp_consent": True})
    assert result.eligible is False
    assert result.matched_facts == ["customer.whatsapp_consent"]
    assert result.unknown_facts == ["order.subtotal_minor"]
    assert result.failed_facts == []


def test_any_group_with_unknown_fact_and_one_real_match_is_eligible() -> None:
    node = RuleGroup(
        logic="any",
        conditions=[
            RuleCondition(fact="customer.whatsapp_consent", operator="is_true"),
            RuleCondition(fact="order.subtotal_minor", operator="gte", value=10000),
        ],
    )
    result = evaluate(node, {"customer.whatsapp_consent": True})
    assert result.eligible is True
    assert result.unknown_facts == ["order.subtotal_minor"]


def test_not_group_with_only_an_unknown_fact_is_eligible_but_flags_unknown() -> None:
    """An unknown condition evaluates as `False` for aggregation purposes
    (per `_eval_node`'s documented contract), so `not` of a single unknown
    condition is vacuously eligible — but the caller must still be able to
    see that the decision rested on an unresolved fact via `unknown_facts`,
    never a silent full pass."""
    node = RuleGroup(
        logic="not",
        conditions=[RuleCondition(fact="order.subtotal_minor", operator="gte", value=10000)],
    )
    result = evaluate(node, {})
    assert result.eligible is True
    assert result.unknown_facts == ["order.subtotal_minor"]
