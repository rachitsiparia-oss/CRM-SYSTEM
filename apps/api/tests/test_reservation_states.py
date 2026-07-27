from app.reservations.states import is_transition_allowed


def test_happy_path_transitions_allowed() -> None:
    assert is_transition_allowed("requested", "pending_review")
    assert is_transition_allowed("pending_review", "approved")
    assert is_transition_allowed("approved", "confirmation_sending")
    assert is_transition_allowed("confirmation_sending", "confirmed")
    assert is_transition_allowed("confirmed", "reminder_scheduled")
    assert is_transition_allowed("reminder_scheduled", "arrived")
    assert is_transition_allowed("arrived", "seated")
    assert is_transition_allowed("seated", "completed")


def test_needs_clarification_loop() -> None:
    assert is_transition_allowed("pending_review", "needs_clarification")
    assert is_transition_allowed("needs_clarification", "pending_review")
    assert is_transition_allowed("needs_clarification", "approved")
    assert is_transition_allowed("needs_clarification", "rejected")


def test_approval_decision_only_from_review_states() -> None:
    assert is_transition_allowed("pending_review", "approved")
    assert is_transition_allowed("pending_review", "rejected")
    assert not is_transition_allowed("requested", "approved")
    assert not is_transition_allowed("requested", "rejected")
    assert not is_transition_allowed("confirmed", "approved")


def test_no_show_only_from_confirmed_or_reminder_scheduled() -> None:
    assert is_transition_allowed("confirmed", "no_show")
    assert is_transition_allowed("reminder_scheduled", "no_show")
    assert not is_transition_allowed("arrived", "no_show")
    assert not is_transition_allowed("approved", "no_show")


def test_cancellation_reachable_up_through_arrived_but_not_after() -> None:
    for state in (
        "pending_review",
        "needs_clarification",
        "approved",
        "confirmation_sending",
        "confirmed",
        "reminder_scheduled",
    ):
        assert is_transition_allowed(state, "cancelled_by_restaurant")
    # A raw, not-yet-reviewed request has no staff engagement yet — only
    # the customer side can "cancel" it (requested -> cancelled_by_customer).
    assert not is_transition_allowed("requested", "cancelled_by_restaurant")
    for state in ("requested", "pending_review", "needs_clarification"):
        assert is_transition_allowed(state, "cancelled_by_customer")
    assert is_transition_allowed("arrived", "cancelled_by_restaurant")
    assert not is_transition_allowed("arrived", "cancelled_by_customer")
    assert not is_transition_allowed("seated", "cancelled_by_customer")
    assert not is_transition_allowed("seated", "cancelled_by_restaurant")


def test_expiry_only_reachable_before_a_decision() -> None:
    assert is_transition_allowed("requested", "expired")
    assert is_transition_allowed("pending_review", "expired")
    assert is_transition_allowed("needs_clarification", "expired")
    assert not is_transition_allowed("approved", "expired")
    assert not is_transition_allowed("confirmed", "expired")


def test_terminal_statuses_have_no_outbound_transitions() -> None:
    terminal = (
        "completed",
        "no_show",
        "cancelled_by_customer",
        "cancelled_by_restaurant",
        "rejected",
        "expired",
    )
    targets = (
        "requested",
        "pending_review",
        "needs_clarification",
        "approved",
        "rejected",
        "confirmation_sending",
        "confirmed",
        "reminder_scheduled",
        "arrived",
        "seated",
        "completed",
        "no_show",
        "cancelled_by_customer",
        "cancelled_by_restaurant",
        "expired",
    )
    for state in terminal:
        for target in targets:
            assert not is_transition_allowed(state, target)


def test_skipping_steps_is_never_allowed() -> None:
    assert not is_transition_allowed("requested", "confirmed")
    assert not is_transition_allowed("requested", "arrived")
    assert not is_transition_allowed("approved", "confirmed")
    assert not is_transition_allowed("confirmation_sending", "arrived")


def test_backward_transitions_are_never_allowed() -> None:
    assert not is_transition_allowed("confirmed", "approved")
    assert not is_transition_allowed("seated", "arrived")
    assert not is_transition_allowed("arrived", "confirmed")


def test_unknown_status_has_no_transitions() -> None:
    assert not is_transition_allowed("nonexistent", "requested")
