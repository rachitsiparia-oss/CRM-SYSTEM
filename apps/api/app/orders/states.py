"""Explicit order status transition rules — this phase's own strict state
machine instruction, the same "backend must reject invalid transitions even
if a client manually constructs a request" principle
app.leads.states applies.

Exact allowed flow (this phase's own instruction, verbatim):
    Draft -> Pending Confirmation -> Confirmed -> Preparing -> Ready ->
    Completed (linear happy path)
Alternative flows (also verbatim, and this is the *complete* list given):
    Pending Confirmation -> Cancelled
    Preparing -> Cancelled
    Ready -> Cancelled
Completed and Cancelled are both terminal.

Cancellation is deliberately NOT reachable from `draft` or `confirmed` —
only the three branches explicitly listed above. This is implemented
literally as given rather than widened with an assumed extra branch: the
instruction is precise and enumerates the alternative flows individually,
and `confirmed` transitions straight to `preparing` in the intended
workflow (kitchen begins immediately on confirmation), so the realistic
cancellation windows the instruction covers are before confirmation, during
preparation, and once ready-but-not-yet-handed-off. See
DATABASE_AND_API.md section 8.7 / this phase's implementation notes for the
full reasoning if this gap ever needs revisiting.
"""

from app.db.models.order import ORDER_STATUSES

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"pending_confirmation"}),
    "pending_confirmation": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"preparing"}),
    "preparing": frozenset({"ready", "cancelled"}),
    "ready": frozenset({"completed", "cancelled"}),
    "completed": frozenset(),
    "cancelled": frozenset(),
}

assert set(ALLOWED_TRANSITIONS) == set(ORDER_STATUSES)


def is_transition_allowed(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())
