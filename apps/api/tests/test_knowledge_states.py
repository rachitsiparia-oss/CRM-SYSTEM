from app.knowledge.states import is_article_transition_allowed


def test_happy_path_to_publish() -> None:
    assert is_article_transition_allowed("draft", "in_review")
    assert is_article_transition_allowed("in_review", "approved")
    assert is_article_transition_allowed("approved", "published")


def test_changes_requested_path() -> None:
    assert is_article_transition_allowed("in_review", "changes_requested")
    assert is_article_transition_allowed("changes_requested", "in_review")
    assert is_article_transition_allowed("changes_requested", "draft")


def test_published_transitions() -> None:
    assert is_article_transition_allowed("published", "draft")
    assert is_article_transition_allowed("published", "archived")
    assert is_article_transition_allowed("published", "superseded")


def test_archived_can_reopen() -> None:
    assert is_article_transition_allowed("archived", "draft")


def test_superseded_can_only_archive() -> None:
    assert is_article_transition_allowed("superseded", "archived")
    assert not is_article_transition_allowed("superseded", "published")
    assert not is_article_transition_allowed("superseded", "draft")


def test_draft_cannot_skip_review() -> None:
    assert not is_article_transition_allowed("draft", "approved")
    assert not is_article_transition_allowed("draft", "published")


def test_same_state_is_not_a_transition() -> None:
    assert not is_article_transition_allowed("draft", "draft")


def test_unknown_status_has_no_transitions() -> None:
    assert not is_article_transition_allowed("nonexistent", "draft")
