import pytest
from app.communications.templates import (
    TemplateRenderError,
    render_template,
    validate_template_variables,
)


def test_validate_accepts_declared_variables() -> None:
    validate_template_variables(
        body="Hi {customer_name}, party of {party_size}.",
        subject=None,
        variables=["customer_name", "party_size"],
    )


def test_validate_rejects_undeclared_variables() -> None:
    with pytest.raises(TemplateRenderError):
        validate_template_variables(
            body="Hi {customer_name}, your total is {total_amount}.",
            subject=None,
            variables=["customer_name"],
        )


def test_validate_checks_subject_too() -> None:
    with pytest.raises(TemplateRenderError):
        validate_template_variables(
            body="Hi {customer_name}.",
            subject="Order {order_number}",
            variables=["customer_name"],
        )


def test_render_substitutes_all_variables() -> None:
    body, subject = render_template(
        body="Hi {customer_name}, table for {party_size}.",
        subject="Reservation {reservation_number}",
        declared_variables=["customer_name", "party_size", "reservation_number"],
        values={"customer_name": "Ananya", "party_size": 4, "reservation_number": "RES-AAAA"},
    )
    assert body == "Hi Ananya, table for 4."
    assert subject == "Reservation RES-AAAA"


def test_render_with_no_subject() -> None:
    body, subject = render_template(
        body="Hi {customer_name}.",
        subject=None,
        declared_variables=["customer_name"],
        values={"customer_name": "Ananya"},
    )
    assert body == "Hi Ananya."
    assert subject is None


def test_render_rejects_missing_variables() -> None:
    with pytest.raises(TemplateRenderError):
        render_template(
            body="Hi {customer_name}, party of {party_size}.",
            subject=None,
            declared_variables=["customer_name", "party_size"],
            values={"customer_name": "Ananya"},
        )


def test_render_rejects_unexpected_variables() -> None:
    with pytest.raises(TemplateRenderError):
        render_template(
            body="Hi {customer_name}.",
            subject=None,
            declared_variables=["customer_name"],
            values={"customer_name": "Ananya", "secret_field": "leak"},
        )


def test_render_never_evaluates_arbitrary_expressions() -> None:
    # A constrained str.format substitution, not eval/exec — a value that
    # looks like a format spec is treated as inert literal text, not code.
    body, _ = render_template(
        body="Message: {customer_name}",
        subject=None,
        declared_variables=["customer_name"],
        values={"customer_name": "{__import__('os')}"},
    )
    assert body == "Message: {__import__('os')}"
