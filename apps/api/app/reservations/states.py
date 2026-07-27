"""Explicit reservation status transition rules — the same
"backend must reject invalid transitions even if a client manually
constructs a request" principle `app.orders.states` and `app.leads.states`
apply.

PROJECT_PLAN.md section 11.1 lists the 14 states (plus this phase's own
`expired` addition — see `app.db.models.reservation`'s module docstring)
without an accompanying transition diagram, unlike Orders' precisely
enumerated flow. The graph below is this phase's own design, following the
states' evident meaning and section 11.2's rules:

    requested -> pending_review -> approved -> confirmation_sending ->
        confirmed -> reminder_scheduled -> arrived -> seated -> completed

Branches:
    pending_review <-> needs_clarification (staff requests more
        information from the guest; resolving it returns to review)
    pending_review / needs_clarification -> approved / rejected (the
        mandatory human review decision, section 11.2)
    requested / pending_review / needs_clarification -> expired (the
        request timed out without a decision — see
        `ReservationSettings.pending_request_expiry_minutes`)
    confirmed / reminder_scheduled -> arrived (a guest may arrive before a
        scheduled reminder fires, especially with a short lead time) or
        no_show (the time slot passed with no arrival)
    Cancellation (`cancelled_by_customer` / `cancelled_by_restaurant`) is
        reachable from every non-terminal state up through `arrived` —
        once `seated`, the guest is actively dining and the reservation's
        own lifecycle ends at `completed`, not a cancellation.

`app.reservations.service.create_walk_in` never calls
`is_transition_allowed`: a walk-in has no prior state to transition from,
it is created already at `arrived` with `approved_by` set to the acting
staff member (see `Reservation`'s module docstring for why that satisfies
the mandatory-approval rule without the asynchronous confirmation flow).
"""

from app.db.models.reservation import RESERVATION_STATUSES

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "requested": frozenset({"pending_review", "cancelled_by_customer", "expired"}),
    "pending_review": frozenset(
        {
            "needs_clarification",
            "approved",
            "rejected",
            "cancelled_by_customer",
            "cancelled_by_restaurant",
            "expired",
        }
    ),
    "needs_clarification": frozenset(
        {
            "pending_review",
            "approved",
            "rejected",
            "cancelled_by_customer",
            "cancelled_by_restaurant",
            "expired",
        }
    ),
    "approved": frozenset(
        {"confirmation_sending", "cancelled_by_customer", "cancelled_by_restaurant"}
    ),
    "rejected": frozenset(),
    "confirmation_sending": frozenset(
        {"confirmed", "cancelled_by_customer", "cancelled_by_restaurant"}
    ),
    "confirmed": frozenset(
        {
            "reminder_scheduled",
            "arrived",
            "no_show",
            "cancelled_by_customer",
            "cancelled_by_restaurant",
        }
    ),
    "reminder_scheduled": frozenset(
        {"arrived", "no_show", "cancelled_by_customer", "cancelled_by_restaurant"}
    ),
    "arrived": frozenset({"seated", "cancelled_by_restaurant"}),
    "seated": frozenset({"completed"}),
    "completed": frozenset(),
    "no_show": frozenset(),
    "cancelled_by_customer": frozenset(),
    "cancelled_by_restaurant": frozenset(),
    "expired": frozenset(),
}

assert set(ALLOWED_TRANSITIONS) == set(RESERVATION_STATUSES)


def is_transition_allowed(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())
