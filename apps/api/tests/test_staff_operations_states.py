from app.staff_operations.profile import is_lifecycle_transition_allowed
from app.staff_operations.reviews import is_review_transition_allowed


def test_lifecycle_happy_path() -> None:
    assert is_lifecycle_transition_allowed("invited", "onboarding")
    assert is_lifecycle_transition_allowed("onboarding", "active")


def test_lifecycle_active_branches() -> None:
    assert is_lifecycle_transition_allowed("active", "on_leave")
    assert is_lifecycle_transition_allowed("active", "suspended")
    assert is_lifecycle_transition_allowed("active", "notice_period")
    assert is_lifecycle_transition_allowed("active", "inactive")


def test_lifecycle_return_from_leave() -> None:
    assert is_lifecycle_transition_allowed("on_leave", "active")


def test_lifecycle_terminated_is_terminal() -> None:
    assert not is_lifecycle_transition_allowed("terminated", "active")
    assert not is_lifecycle_transition_allowed("terminated", "onboarding")


def test_lifecycle_notice_period_to_terminated() -> None:
    assert is_lifecycle_transition_allowed("notice_period", "terminated")


def test_lifecycle_inactive_can_reactivate() -> None:
    assert is_lifecycle_transition_allowed("inactive", "active")


def test_lifecycle_unknown_status_has_no_transitions() -> None:
    assert not is_lifecycle_transition_allowed("nonexistent", "active")


def test_review_happy_path() -> None:
    assert is_review_transition_allowed("draft", "in_progress")
    assert is_review_transition_allowed("in_progress", "submitted")
    assert is_review_transition_allowed("submitted", "reviewed")
    assert is_review_transition_allowed("reviewed", "finalized")
    assert is_review_transition_allowed("finalized", "acknowledged")


def test_review_can_be_sent_back_for_more_input() -> None:
    assert is_review_transition_allowed("submitted", "in_progress")


def test_review_acknowledged_is_terminal() -> None:
    assert not is_review_transition_allowed("acknowledged", "finalized")
    assert not is_review_transition_allowed("acknowledged", "draft")


def test_review_cannot_skip_to_finalized() -> None:
    assert not is_review_transition_allowed("draft", "finalized")
    assert not is_review_transition_allowed("submitted", "finalized")
