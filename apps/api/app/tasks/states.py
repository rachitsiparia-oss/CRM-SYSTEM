"""Explicit `TaskRecord.status` transitions — same discipline as
`app.leads.states`/`app.reservations.states`/`app.communications.states`.
"""

from app.db.models.task_record import TASK_STATUSES

TASK_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"in_progress", "blocked", "completed", "cancelled"}),
    "in_progress": frozenset({"blocked", "completed", "cancelled", "open"}),
    "blocked": frozenset({"in_progress", "open", "cancelled"}),
    "completed": frozenset({"open"}),
    "cancelled": frozenset({"open"}),
}

assert set(TASK_TRANSITIONS) == set(TASK_STATUSES)


def is_task_transition_allowed(current: str, target: str) -> bool:
    if current == target:
        return False
    return target in TASK_TRANSITIONS.get(current, frozenset())
