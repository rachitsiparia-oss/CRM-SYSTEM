"""Domain/service-level tests for the internal customer-credit module —
`app.customer_credit.ledger` and `app.customer_credit.accounts`. Mirrors
`test_loyalty_ledger.py`'s pattern (both ledgers are built to the same
signed-entry, idempotency-keyed, `SELECT ... FOR UPDATE`-locked contract).
"""

import uuid
from collections.abc import Awaitable, Callable

import pytest
from app.customer_credit import accounts as accounts_service
from app.customer_credit import ledger
from app.customer_credit.errors import (
    AlreadyReversedError,
    DuplicateIdempotencyKeyError,
    InsufficientCreditError,
)
from app.customer_credit.schemas import (
    AdjustIn,
    EnsureAccountIn,
    IssueIn,
    RedeemIn,
    ReverseIn,
)
from app.db.models import Customer, CustomerCreditAccount, StaffUser
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

MakeStaffUser = Callable[..., Awaitable[StaffUser]]


async def make_customer(session: AsyncSession, **overrides: object) -> Customer:
    suffix = uuid.uuid4().hex[:10]
    fields: dict[str, object] = {
        "id": uuid.uuid4(),
        "customer_number": f"CUST-{suffix}",
        "display_name": f"Customer {suffix}",
        "first_name": "Test",
        "last_name": "Customer",
    }
    fields.update(overrides)
    customer = Customer(**fields)
    session.add(customer)
    await session.flush()
    return customer


async def make_account(
    session: AsyncSession, *, actor: StaffUser, customer: Customer
) -> CustomerCreditAccount:
    return await accounts_service.ensure_account(
        session, actor=actor, payload=EnsureAccountIn(customer_id=customer.id)
    )


def _idem() -> str:
    return f"idem-{uuid.uuid4().hex}"


# --- Account ensure ------------------------------------------------------


async def test_ensure_account_is_idempotent_per_customer(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)

    first = await accounts_service.ensure_account(
        db_session, actor=actor, payload=EnsureAccountIn(customer_id=customer.id)
    )
    second = await accounts_service.ensure_account(
        db_session, actor=actor, payload=EnsureAccountIn(customer_id=customer.id)
    )
    assert first.id == second.id
    assert first.current_balance_minor == 0


# --- issue/redeem/adjust sign handling ---------------------------------------


async def test_issue_credits_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)

    entry = await accounts_service.issue(
        db_session,
        actor=actor,
        payload=IssueIn(
            account_id=account.id,
            amount_minor=5000,
            issue_reason="service_recovery",
            idempotency_key=_idem(),
        ),
    )
    assert entry.amount_delta_minor == 5000
    await db_session.refresh(account)
    assert account.current_balance_minor == 5000


async def test_redeem_debits_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)
    await accounts_service.issue(
        db_session,
        actor=actor,
        payload=IssueIn(
            account_id=account.id,
            amount_minor=5000,
            issue_reason="service_recovery",
            idempotency_key=_idem(),
        ),
    )

    entry = await accounts_service.redeem(
        db_session,
        actor=actor,
        payload=RedeemIn(account_id=account.id, amount_minor=2000, idempotency_key=_idem()),
    )
    assert entry.amount_delta_minor == -2000
    await db_session.refresh(account)
    assert account.current_balance_minor == 3000


async def test_adjust_requires_is_credit_at_ledger_level(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)

    with pytest.raises(ValueError):
        await ledger.post_entry(
            db_session,
            account_id=account.id,
            entry_type="adjust",
            amount_minor=500,
            idempotency_key=_idem(),
            actor_id=actor.id,
        )


async def test_adjust_positive_delta_increases_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)

    entry = await accounts_service.adjust(
        db_session,
        actor=actor,
        payload=AdjustIn(
            account_id=account.id,
            amount_delta_minor=750,
            reason="goodwill",
            idempotency_key=_idem(),
        ),
    )
    assert entry.amount_delta_minor == 750
    await db_session.refresh(account)
    assert account.current_balance_minor == 750


async def test_adjust_negative_delta_decreases_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)
    await accounts_service.issue(
        db_session,
        actor=actor,
        payload=IssueIn(
            account_id=account.id,
            amount_minor=1000,
            issue_reason="service_recovery",
            idempotency_key=_idem(),
        ),
    )

    entry = await accounts_service.adjust(
        db_session,
        actor=actor,
        payload=AdjustIn(
            account_id=account.id,
            amount_delta_minor=-400,
            reason="correction",
            idempotency_key=_idem(),
        ),
    )
    assert entry.amount_delta_minor == -400
    await db_session.refresh(account)
    assert account.current_balance_minor == 600


# --- Idempotency and insufficient balance ------------------------------------


async def test_duplicate_idempotency_key_rejected(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)
    key = _idem()

    await accounts_service.issue(
        db_session,
        actor=actor,
        payload=IssueIn(
            account_id=account.id,
            amount_minor=1000,
            issue_reason="service_recovery",
            idempotency_key=key,
        ),
    )
    with pytest.raises(DuplicateIdempotencyKeyError):
        await accounts_service.issue(
            db_session,
            actor=actor,
            payload=IssueIn(
                account_id=account.id,
                amount_minor=1000,
                issue_reason="service_recovery",
                idempotency_key=key,
            ),
        )
    await db_session.refresh(account)
    assert account.current_balance_minor == 1000  # not doubled


async def test_redeem_more_than_balance_raises_insufficient_credit(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)

    with pytest.raises(InsufficientCreditError):
        await accounts_service.redeem(
            db_session,
            actor=actor,
            payload=RedeemIn(account_id=account.id, amount_minor=100, idempotency_key=_idem()),
        )


# --- Reversal ------------------------------------------------------------


async def test_reverse_undoes_balance(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)
    original = await accounts_service.issue(
        db_session,
        actor=actor,
        payload=IssueIn(
            account_id=account.id,
            amount_minor=1000,
            issue_reason="service_recovery",
            idempotency_key=_idem(),
        ),
    )

    reversal = await accounts_service.reverse(
        db_session,
        actor=actor,
        payload=ReverseIn(entry_id=original.id, reason="mistake", idempotency_key=_idem()),
    )
    assert reversal.amount_delta_minor == -1000
    assert reversal.reversal_of_id == original.id
    await db_session.refresh(account)
    assert account.current_balance_minor == 0


async def test_reverse_twice_raises_already_reversed(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)
    original = await accounts_service.issue(
        db_session,
        actor=actor,
        payload=IssueIn(
            account_id=account.id,
            amount_minor=1000,
            issue_reason="service_recovery",
            idempotency_key=_idem(),
        ),
    )
    await accounts_service.reverse(
        db_session,
        actor=actor,
        payload=ReverseIn(entry_id=original.id, reason="mistake", idempotency_key=_idem()),
    )

    with pytest.raises(AlreadyReversedError):
        await accounts_service.reverse(
            db_session,
            actor=actor,
            payload=ReverseIn(entry_id=original.id, reason="again", idempotency_key=_idem()),
        )


async def test_reversing_a_reversal_raises_already_reversed(
    db_session: AsyncSession, make_staff_user: MakeStaffUser
) -> None:
    actor = await make_staff_user(role_code="owner")
    customer = await make_customer(db_session)
    account = await make_account(db_session, actor=actor, customer=customer)
    original = await accounts_service.issue(
        db_session,
        actor=actor,
        payload=IssueIn(
            account_id=account.id,
            amount_minor=1000,
            issue_reason="service_recovery",
            idempotency_key=_idem(),
        ),
    )
    reversal = await accounts_service.reverse(
        db_session,
        actor=actor,
        payload=ReverseIn(entry_id=original.id, reason="mistake", idempotency_key=_idem()),
    )

    with pytest.raises(AlreadyReversedError):
        await accounts_service.reverse(
            db_session,
            actor=actor,
            payload=ReverseIn(entry_id=reversal.id, reason="oops", idempotency_key=_idem()),
        )
