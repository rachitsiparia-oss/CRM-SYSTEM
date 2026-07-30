from app.tasks.states import is_task_transition_allowed


def test_happy_path() -> None:
    assert is_task_transition_allowed("open", "in_progress")
    assert is_task_transition_allowed("in_progress", "completed")


def test_blocked_and_unblocked() -> None:
    assert is_task_transition_allowed("open", "blocked")
    assert is_task_transition_allowed("in_progress", "blocked")
    assert is_task_transition_allowed("blocked", "in_progress")
    assert is_task_transition_allowed("blocked", "open")


def test_cancellation_reachable_from_active_states() -> None:
    for state in ("open", "in_progress", "blocked"):
        assert is_task_transition_allowed(state, "cancelled")


def test_reopen_from_terminal_states() -> None:
    assert is_task_transition_allowed("completed", "open")
    assert is_task_transition_allowed("cancelled", "open")


def test_terminal_states_have_only_reopen() -> None:
    for terminal in ("completed", "cancelled"):
        assert not is_task_transition_allowed(terminal, "in_progress")
        assert not is_task_transition_allowed(terminal, "blocked")
        assert not is_task_transition_allowed(terminal, "cancelled")
        assert not is_task_transition_allowed(terminal, "completed")


def test_same_state_is_not_a_transition() -> None:
    assert not is_task_transition_allowed("open", "open")


def test_unknown_status_has_no_transitions() -> None:
    assert not is_task_transition_allowed("nonexistent", "open")
