import pytest
from app.shared.normalization import (
    NormalizationError,
    normalize_email,
    normalize_phone,
    normalize_search_text,
    normalize_tag_name,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("9876543210", "+919876543210"),
        ("+91 98765 43210", "+919876543210"),
        ("091-98765-43210", "+919876543210"),
        ("919876543210", "+919876543210"),
        ("  9876543210  ", "+919876543210"),
    ],
)
def test_normalize_phone_variants(raw: str, expected: str) -> None:
    assert normalize_phone(raw) == expected


def test_normalize_phone_none_and_empty() -> None:
    assert normalize_phone(None) is None
    assert normalize_phone("   ") is None


def test_normalize_phone_rejects_invalid() -> None:
    with pytest.raises(NormalizationError):
        normalize_phone("12345")


def test_normalize_email_lowercases_and_trims() -> None:
    assert normalize_email("  Test.User@Example.COM ") == "test.user@example.com"


def test_normalize_email_rejects_invalid() -> None:
    with pytest.raises(NormalizationError):
        normalize_email("not-an-email")


def test_normalize_email_none_and_empty() -> None:
    assert normalize_email(None) is None
    assert normalize_email("") is None


def test_normalize_tag_name_collapses_whitespace_and_case() -> None:
    assert normalize_tag_name("  VIP   Customer  ") == "vip customer"


def test_normalize_tag_name_rejects_empty() -> None:
    with pytest.raises(NormalizationError):
        normalize_tag_name("   ")


def test_normalize_search_text() -> None:
    assert normalize_search_text("  Ananya   Rao ") == "ananya rao"
