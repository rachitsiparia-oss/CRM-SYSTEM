from app.orders.states import is_transition_allowed


def test_happy_path_transitions_allowed() -> None:
    assert is_transition_allowed("draft", "pending_confirmation")
    assert is_transition_allowed("pending_confirmation", "confirmed")
    assert is_transition_allowed("confirmed", "preparing")
    assert is_transition_allowed("preparing", "ready")
    assert is_transition_allowed("ready", "completed")


def test_cancellation_allowed_only_from_the_three_named_states() -> None:
    assert is_transition_allowed("pending_confirmation", "cancelled")
    assert is_transition_allowed("preparing", "cancelled")
    assert is_transition_allowed("ready", "cancelled")
    assert not is_transition_allowed("draft", "cancelled")
    assert not is_transition_allowed("confirmed", "cancelled")


def test_completed_and_cancelled_are_terminal() -> None:
    for target in (
        "draft",
        "pending_confirmation",
        "confirmed",
        "preparing",
        "ready",
        "completed",
        "cancelled",
    ):
        assert not is_transition_allowed("completed", target)
        assert not is_transition_allowed("cancelled", target)


def test_skipping_steps_is_never_allowed() -> None:
    assert not is_transition_allowed("draft", "confirmed")
    assert not is_transition_allowed("draft", "preparing")
    assert not is_transition_allowed("draft", "ready")
    assert not is_transition_allowed("draft", "completed")
    assert not is_transition_allowed("pending_confirmation", "preparing")
    assert not is_transition_allowed("confirmed", "ready")
    assert not is_transition_allowed("confirmed", "completed")


def test_backward_transitions_are_never_allowed() -> None:
    assert not is_transition_allowed("preparing", "confirmed")
    assert not is_transition_allowed("ready", "preparing")
    assert not is_transition_allowed("confirmed", "pending_confirmation")


def test_unknown_status_has_no_transitions() -> None:
    assert not is_transition_allowed("nonexistent", "draft")
