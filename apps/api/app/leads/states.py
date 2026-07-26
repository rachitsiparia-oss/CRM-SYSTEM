"""Explicit lead status transition rules —
ARCHITECTURE_AND_TECH_STACK.md section 7.6 ("Use explicit allowed
transitions... invalid transitions must be rejected by the backend even if
a client manually constructs a request").

`won` is deliberately not reachable through `is_transition_allowed` at all
— it can only be set by `app.leads.service.execute_conversion`, per this
phase's own instruction ("Conversion must occur through the conversion
service, not by directly patching status to Converted").
"""

from app.db.models.lead import LEAD_STATUSES

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "new": frozenset({"contacted", "qualified", "lost", "closed"}),
    "contacted": frozenset({"qualified", "interested", "follow_up_scheduled", "lost", "closed"}),
    "qualified": frozenset(
        {"interested", "follow_up_scheduled", "proposal_shared", "lost", "closed"}
    ),
    "interested": frozenset(
        {"follow_up_scheduled", "proposal_shared", "negotiating", "lost", "closed"}
    ),
    "follow_up_scheduled": frozenset(
        {"qualified", "interested", "proposal_shared", "negotiating", "lost", "closed"}
    ),
    "proposal_shared": frozenset({"negotiating", "lost", "closed"}),
    "negotiating": frozenset({"proposal_shared", "lost", "closed"}),
    "won": frozenset({"closed"}),
    # Reopening a lost lead is allowed (CORE_CRM_MODULES.md section 5.15,
    # "lost lead reopened") but only back to `new`, so it re-enters the
    # pipeline from the start rather than skipping qualification.
    "lost": frozenset({"new", "closed"}),
    "closed": frozenset(),
}

assert set(ALLOWED_TRANSITIONS) == set(LEAD_STATUSES)


def is_transition_allowed(current: str, target: str) -> bool:
    if target == "won":
        return False
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())
