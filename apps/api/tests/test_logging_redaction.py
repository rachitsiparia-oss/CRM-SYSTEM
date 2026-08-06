from app.core.logging import _redact_sensitive_fields


def test_redacts_known_sensitive_key_names() -> None:
    event_dict = {
        "event": "integration_call",
        "password": "hunter2",
        "api_key": "sk-live-abc123",
        "Authorization": "Bearer eyJ...",
        "service_role_key": "sbp_secret",
        "signature": "deadbeef",
        "otp": "123456",
        "card_number": "4111111111111111",
    }
    result = _redact_sensitive_fields(None, "info", dict(event_dict))
    for key in event_dict:
        if key == "event":
            continue
        assert result[key] == "[REDACTED]"


def test_leaves_non_sensitive_fields_untouched() -> None:
    event_dict = {"event": "order_created", "order_id": "abc-123", "total_minor": 4599}
    result = _redact_sensitive_fields(None, "info", dict(event_dict))
    assert result == event_dict


def test_matches_key_names_case_insensitively_and_as_substring() -> None:
    event_dict = {"REQUEST_TOKEN": "xyz", "user_secret_note": "should be redacted too"}
    result = _redact_sensitive_fields(None, "info", dict(event_dict))
    assert result["REQUEST_TOKEN"] == "[REDACTED]"
    assert result["user_secret_note"] == "[REDACTED]"
