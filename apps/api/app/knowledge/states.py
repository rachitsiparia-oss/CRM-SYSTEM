"""Article review/approval/publication lifecycle — this phase's own
instruction section 2/4: "Define and enforce valid transitions." No status
transition table exists in any canonical document; this graph is designed
here, the same situation Phase 8 was in for recipes/wastage.
"""

ARTICLE_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"in_review"}),
    "in_review": frozenset({"approved", "changes_requested"}),
    "changes_requested": frozenset({"in_review", "draft"}),
    "approved": frozenset({"published", "draft"}),
    "published": frozenset({"draft", "archived", "superseded"}),
    "superseded": frozenset({"archived"}),
    "archived": frozenset({"draft"}),
}


def is_article_transition_allowed(current: str, target: str) -> bool:
    return target in ARTICLE_TRANSITIONS.get(current, frozenset())
