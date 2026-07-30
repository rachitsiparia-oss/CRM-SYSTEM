from app.communications.states import (
    is_conversation_transition_allowed,
    is_message_transition_allowed,
)


def test_conversation_happy_path() -> None:
    assert is_conversation_transition_allowed("open", "waiting_on_customer")
    assert is_conversation_transition_allowed("waiting_on_customer", "waiting_on_staff")
    assert is_conversation_transition_allowed("waiting_on_staff", "resolved")
    assert is_conversation_transition_allowed("resolved", "closed")


def test_conversation_reopen_from_terminal_states() -> None:
    assert is_conversation_transition_allowed("resolved", "open")
    assert is_conversation_transition_allowed("closed", "open")
    assert is_conversation_transition_allowed("spam", "open")


def test_conversation_snooze_and_unsnooze() -> None:
    assert is_conversation_transition_allowed("open", "snoozed")
    assert is_conversation_transition_allowed("snoozed", "open")
    assert is_conversation_transition_allowed("snoozed", "waiting_on_staff")


def test_conversation_same_state_is_not_a_transition() -> None:
    assert not is_conversation_transition_allowed("open", "open")


def test_conversation_closed_has_only_reopen() -> None:
    assert not is_conversation_transition_allowed("closed", "resolved")
    assert not is_conversation_transition_allowed("closed", "spam")
    assert is_conversation_transition_allowed("closed", "open")


def test_conversation_spam_reachable_from_open_states() -> None:
    for state in ("open", "pending", "waiting_on_customer", "waiting_on_staff"):
        assert is_conversation_transition_allowed(state, "spam")


def test_conversation_unknown_status_has_no_transitions() -> None:
    assert not is_conversation_transition_allowed("nonexistent", "open")


# --- Message state machine ----------------------------------------------


def test_outbound_happy_path() -> None:
    assert is_message_transition_allowed("outbound", "draft", "queued")
    assert is_message_transition_allowed("outbound", "queued", "processing")
    assert is_message_transition_allowed("outbound", "processing", "sent")
    assert is_message_transition_allowed("outbound", "sent", "delivered")
    assert is_message_transition_allowed("outbound", "delivered", "read")


def test_outbound_failure_and_retry() -> None:
    assert is_message_transition_allowed("outbound", "processing", "failed")
    assert is_message_transition_allowed("outbound", "sent", "failed")
    assert is_message_transition_allowed("outbound", "failed", "queued")


def test_outbound_no_regression_past_delivered_or_read() -> None:
    # This phase's own instruction section 16: an out-of-order webhook must
    # never regress a message from a more advanced status to an earlier one.
    assert not is_message_transition_allowed("outbound", "failed", "read")
    assert not is_message_transition_allowed("outbound", "cancelled", "sent")
    assert not is_message_transition_allowed("outbound", "delivered", "queued")
    assert not is_message_transition_allowed("outbound", "suppressed", "processing")
    assert not is_message_transition_allowed("outbound", "read", "delivered")


def test_outbound_terminal_states_have_no_transitions() -> None:
    for terminal in ("read", "cancelled", "suppressed"):
        assert not is_message_transition_allowed("outbound", terminal, "queued")
        assert not is_message_transition_allowed("outbound", terminal, "sent")


def test_inbound_happy_path() -> None:
    assert is_message_transition_allowed("inbound", "received", "processed")
    assert is_message_transition_allowed("inbound", "processed", "assigned")
    assert is_message_transition_allowed("inbound", "assigned", "replied")
    assert is_message_transition_allowed("inbound", "replied", "resolved")


def test_inbound_spam_reachable_early() -> None:
    assert is_message_transition_allowed("inbound", "received", "spam")
    assert is_message_transition_allowed("inbound", "processed", "spam")
    assert not is_message_transition_allowed("inbound", "assigned", "spam")


def test_internal_notes_never_transition() -> None:
    assert not is_message_transition_allowed("internal", "created", "created")
    assert not is_message_transition_allowed("internal", "created", "sent")
