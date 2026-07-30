"""Explicit state machines for `Conversation.status` and
`Message.delivery_status` — ARCHITECTURE_AND_TECH_STACK.md section 7.6
("use explicit allowed transitions... invalid transitions must be rejected
by the backend"), the same discipline `app.leads.states`/
`app.reservations.states` already apply.

The message transition graph is itself the "no regression" guarantee this
phase's own instruction requires for delivery-status webhooks (section 16):
`delivered` has no edge back to `queued`, `read` has no edge back to
`delivered`, etc. A caller attempting a transition not present in the graph
gets `False` back and must treat it as a no-op, not an error — an
out-of-order webhook is expected traffic, not a bug.
"""

from app.db.models.conversation import CONVERSATION_STATUSES
from app.db.models.message import (
    ALL_MESSAGE_STATUSES,
    INBOUND_MESSAGE_STATUSES,
    INTERNAL_MESSAGE_STATUSES,
    OUTBOUND_MESSAGE_STATUSES,
)

CONVERSATION_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset(
        {"pending", "waiting_on_customer", "waiting_on_staff", "snoozed", "resolved", "spam"}
    ),
    "pending": frozenset(
        {"open", "waiting_on_customer", "waiting_on_staff", "snoozed", "resolved", "spam"}
    ),
    "waiting_on_customer": frozenset({"waiting_on_staff", "open", "resolved", "snoozed", "spam"}),
    "waiting_on_staff": frozenset({"waiting_on_customer", "open", "resolved", "snoozed", "spam"}),
    "snoozed": frozenset({"open", "waiting_on_customer", "waiting_on_staff", "resolved"}),
    "resolved": frozenset({"open", "closed"}),
    "closed": frozenset({"open"}),
    "spam": frozenset({"open", "closed"}),
}

assert set(CONVERSATION_TRANSITIONS) == set(CONVERSATION_STATUSES)


def is_conversation_transition_allowed(current: str, target: str) -> bool:
    if current == target:
        return False
    return target in CONVERSATION_TRANSITIONS.get(current, frozenset())


OUTBOUND_MESSAGE_TRANSITIONS: dict[str, frozenset[str]] = {
    "draft": frozenset({"queued", "cancelled"}),
    "queued": frozenset({"processing", "cancelled", "suppressed"}),
    "processing": frozenset({"sent", "failed"}),
    "sent": frozenset({"delivered", "failed"}),
    "delivered": frozenset({"read"}),
    "read": frozenset(),
    # A retryable failure re-queues (a new `MessageDeliveryAttempt` row
    # records the retry itself); a permanent failure has no outgoing edge.
    "failed": frozenset({"queued"}),
    "cancelled": frozenset(),
    "suppressed": frozenset(),
}
assert set(OUTBOUND_MESSAGE_TRANSITIONS) == set(OUTBOUND_MESSAGE_STATUSES)

INBOUND_MESSAGE_TRANSITIONS: dict[str, frozenset[str]] = {
    "received": frozenset({"processed", "spam"}),
    "processed": frozenset({"assigned", "spam"}),
    "assigned": frozenset({"replied", "resolved"}),
    "replied": frozenset({"resolved", "assigned"}),
    "resolved": frozenset(),
    "spam": frozenset(),
}
assert set(INBOUND_MESSAGE_TRANSITIONS) == set(INBOUND_MESSAGE_STATUSES)

assert set(OUTBOUND_MESSAGE_TRANSITIONS) | set(INBOUND_MESSAGE_TRANSITIONS) | set(
    INTERNAL_MESSAGE_STATUSES
) == set(ALL_MESSAGE_STATUSES)


def is_message_transition_allowed(direction: str, current: str, target: str) -> bool:
    if current == target:
        return False
    if direction == "outbound":
        return target in OUTBOUND_MESSAGE_TRANSITIONS.get(current, frozenset())
    if direction == "inbound":
        return target in INBOUND_MESSAGE_TRANSITIONS.get(current, frozenset())
    return False  # internal notes never transition past "created"
