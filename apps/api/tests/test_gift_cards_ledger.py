"""Domain/service-level tests for the gift card module —
`app.gift_cards.security`, `app.gift_cards.service`, `app.gift_cards.ledger`,
and `app.gift_cards.redemption`. Mirrors `test_loyalty_ledger.py`'s pattern
for the shared ledger contract, plus the card-specific status lifecycle and
code/PIN hashing this domain adds on top.
"""

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from app.db.models import GiftCard, StaffUser
from app.gift_cards import ledger, redemption, security, service
from app.gift_cards.errors import (
    AlreadyReversedError,
    DuplicateIdempotencyKeyError,
    GiftCardNotRedeemableError,
    InsufficientBalanceError,
    InvalidCodeError,
    InvalidPinError,
    InvalidStatusTransitionError,
)
from app.gift_cards.schemas import AdjustGiftCardIn, IssueGiftCardIn
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def issue_and_activate_card(
    session: AsyncSession,
    *,
    actor: StaffUser,
    initial_amount_minor: int = 10000,
    **overrides: Any,
) -> tuple[GiftCard, str]:
    fields: dict[str, Any] = {
        "initial_amount_minor": initial_amount_minor,
        "idempotency_key": f"idem-{uuid.uuid4().hex}",
    }
    fields.update(overrides)
    card, code = await service.issue_card(session, actor=actor, payload=IssueGiftCardIn(**fields))
    card = await service.activate_card(session, actor=actor, card=card)
    return card, code


def _idem() -> str:
    return f"idem-{uuid.uuid4().hex}"


# --- Code/PIN hashing ----------------------------------------------------


async def test_code_round_trip_verifies_correctly() -> None:
    code = security.generate_code()
    hashed = security.hash_code(code)
    assert security.verify_code(code, hashed) is True


async def test_code_round_trip_rejects_wrong_code() -> None:
    code = security.generate_code()
    hashed = security.hash_code(code)
    wrong = security.generate_code()
    assert security.verify_code(wrong, hashed) is False


async def test_pin_round_trip_verifies_correctly() -> None:
    pin_hash = security.hash_pin("4242")
    assert security.verify_pin("4242", pin_hash) is True


async def test_pin_round_trip_rejects_wrong_pin() -> None:
    pin_hash = security.hash_pin("4242")
    assert security.verify_pin("9999", pin_hash) is False


# --- Issuance and activation ---------------------------------------------


async def test_issue_card_creates_draft_with_full_balance_posted(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    key = _idem()
    card, code = await service.issue_card(
        db_session,
        actor=actor,
        payload=IssueGiftCardIn(initial_amount_minor=5000, idempotency_key=key),
    )
    assert card.status == "draft"
    assert card.current_balance_minor == 5000
    assert len(code) == 16

    entry = await ledger.find_by_idempotency_key(db_session, key)
    assert entry is not None
    assert entry.entry_type == "issue"
    assert entry.amount_delta_minor == 5000
    assert entry.balance_after_minor == 5000


async def test_activate_card_transitions_draft_to_active(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, _code = await service.issue_card(
        db_session,
        actor=actor,
        payload=IssueGiftCardIn(initial_amount_minor=5000, idempotency_key=_idem()),
    )
    activated = await service.activate_card(db_session, actor=actor, card=card)
    assert activated.status == "active"
    assert activated.activated_at is not None


async def test_activate_card_rejects_non_draft_status(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, _code = await issue_and_activate_card(db_session, actor=actor)
    with pytest.raises(InvalidStatusTransitionError):
        await service.activate_card(db_session, actor=actor, card=card)


# --- Redemption ------------------------------------------------------------


async def test_redeem_by_code_rejects_unrecognized_code(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    with pytest.raises(InvalidCodeError):
        await redemption.redeem_by_code(
            db_session,
            actor=actor,
            code="NOTAREALCODE1234",
            pin=None,
            amount_minor=100,
            order_id=None,
            idempotency_key=_idem(),
        )


async def test_redeem_by_code_rejects_wrong_pin(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, code = await issue_and_activate_card(db_session, actor=actor, pin="1234")
    with pytest.raises(InvalidPinError):
        await redemption.redeem_by_code(
            db_session,
            actor=actor,
            code=code,
            pin="0000",
            amount_minor=100,
            order_id=None,
            idempotency_key=_idem(),
        )


async def test_redeem_by_code_rejects_non_redeemable_status(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    # Draft (not yet activated) is not in the redeemable status set.
    card, code = await service.issue_card(
        db_session,
        actor=actor,
        payload=IssueGiftCardIn(initial_amount_minor=5000, idempotency_key=_idem()),
    )
    with pytest.raises(GiftCardNotRedeemableError):
        await redemption.redeem_by_code(
            db_session,
            actor=actor,
            code=code,
            pin=None,
            amount_minor=100,
            order_id=None,
            idempotency_key=_idem(),
        )


async def test_redeem_moves_status_active_to_partial_to_fully_redeemed(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, code = await issue_and_activate_card(db_session, actor=actor, initial_amount_minor=10000)
    assert card.status == "active"

    await redemption.redeem_by_code(
        db_session,
        actor=actor,
        code=code,
        pin=None,
        amount_minor=4000,
        order_id=None,
        idempotency_key=_idem(),
    )
    await db_session.refresh(card)
    assert card.current_balance_minor == 6000
    assert card.status == "partially_redeemed"

    await redemption.redeem_by_code(
        db_session,
        actor=actor,
        code=code,
        pin=None,
        amount_minor=6000,
        order_id=None,
        idempotency_key=_idem(),
    )
    await db_session.refresh(card)
    assert card.current_balance_minor == 0
    assert card.status == "fully_redeemed"


async def test_redemption_never_allows_negative_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, code = await issue_and_activate_card(db_session, actor=actor, initial_amount_minor=1000)
    with pytest.raises(InsufficientBalanceError):
        await redemption.redeem_by_code(
            db_session,
            actor=actor,
            code=code,
            pin=None,
            amount_minor=1001,
            order_id=None,
            idempotency_key=_idem(),
        )
    await db_session.refresh(card)
    assert card.current_balance_minor == 1000


async def test_redeem_duplicate_idempotency_key_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, code = await issue_and_activate_card(db_session, actor=actor, initial_amount_minor=10000)
    key = _idem()
    await redemption.redeem_by_code(
        db_session,
        actor=actor,
        code=code,
        pin=None,
        amount_minor=1000,
        order_id=None,
        idempotency_key=key,
    )
    with pytest.raises(DuplicateIdempotencyKeyError):
        await redemption.redeem_by_code(
            db_session,
            actor=actor,
            code=code,
            pin=None,
            amount_minor=1000,
            order_id=None,
            idempotency_key=key,
        )
    await db_session.refresh(card)
    assert card.current_balance_minor == 9000  # not doubled


# --- Reversal ------------------------------------------------------------


async def test_reverse_redemption_restores_balance_and_status(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, code = await issue_and_activate_card(db_session, actor=actor, initial_amount_minor=10000)
    entry = await redemption.redeem_by_code(
        db_session,
        actor=actor,
        code=code,
        pin=None,
        amount_minor=4000,
        order_id=None,
        idempotency_key=_idem(),
    )
    await db_session.refresh(card)
    assert card.status == "partially_redeemed"

    await redemption.reverse_redemption(
        db_session, actor=actor, entry=entry, reason="mistaken redemption", idempotency_key=_idem()
    )
    await db_session.refresh(card)
    assert card.current_balance_minor == 10000
    assert card.status == "active"


async def test_reverse_redemption_twice_raises_already_reversed(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, code = await issue_and_activate_card(db_session, actor=actor, initial_amount_minor=10000)
    entry = await redemption.redeem_by_code(
        db_session,
        actor=actor,
        code=code,
        pin=None,
        amount_minor=4000,
        order_id=None,
        idempotency_key=_idem(),
    )
    await redemption.reverse_redemption(
        db_session, actor=actor, entry=entry, reason="mistake", idempotency_key=_idem()
    )
    with pytest.raises(AlreadyReversedError):
        await redemption.reverse_redemption(
            db_session, actor=actor, entry=entry, reason="again", idempotency_key=_idem()
        )


# --- Cancel/expire zero out remaining balance --------------------------------


async def test_cancel_card_zeroes_remaining_balance_via_ledger_entry(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, _code = await issue_and_activate_card(db_session, actor=actor, initial_amount_minor=5000)
    cancelled = await service.cancel_card(db_session, actor=actor, card=card, reason="test cancel")
    assert cancelled.status == "cancelled"
    assert cancelled.current_balance_minor == 0

    latest = await ledger.find_by_idempotency_key(db_session, f"gift-card-cancel:{card.id}")
    assert latest is not None
    assert latest.entry_type == "cancel"
    assert latest.amount_delta_minor == -5000


async def test_expire_card_zeroes_remaining_balance_via_ledger_entry(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    card, _code = await issue_and_activate_card(db_session, actor=actor, initial_amount_minor=5000)
    expired = await service.expire_card(db_session, actor=actor, card=card)
    assert expired.status == "expired"
    assert expired.current_balance_minor == 0

    latest = await ledger.find_by_idempotency_key(db_session, f"gift-card-expire:{card.id}")
    assert latest is not None
    assert latest.entry_type == "expire"
    assert latest.amount_delta_minor == -5000


async def test_cancel_card_with_zero_balance_posts_no_ledger_entry(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    """A card whose balance is already zero shouldn't produce a spurious
    zero-magnitude ledger entry — `post_entry` itself would reject a
    non-positive amount, so `cancel_card` must skip the ledger call
    entirely when there is nothing left to zero out.

    Full redemption alone can't set up this case: `post_entry` auto-flips
    status to `fully_redeemed` as the balance hits zero, and
    `fully_redeemed` isn't cancellable. `suspended` is the one status
    `post_entry` deliberately excludes from that auto-transition (so a
    suspended card's balance can be adjusted to zero via `adjust_card`
    while remaining `suspended`, and therefore still cancellable).
    """
    actor = await make_staff_user(role_code="owner")
    card, _code = await issue_and_activate_card(db_session, actor=actor, initial_amount_minor=1000)
    await service.suspend_card(db_session, actor=actor, card=card, reason="fraud review")
    assert card.status == "suspended"

    await service.adjust_card(
        db_session,
        actor=actor,
        card=card,
        payload=AdjustGiftCardIn(
            amount_delta_minor=-1000, reason="zero out", idempotency_key=_idem()
        ),
    )
    await db_session.refresh(card)
    assert card.current_balance_minor == 0
    assert card.status == "suspended"  # unchanged by the adjust — this status is excluded

    cancelled = await service.cancel_card(db_session, actor=actor, card=card, reason="cleanup")
    assert cancelled.status == "cancelled"
    latest = await ledger.find_by_idempotency_key(db_session, f"gift-card-cancel:{card.id}")
    assert latest is None
