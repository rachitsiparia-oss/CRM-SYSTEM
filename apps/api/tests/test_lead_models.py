import uuid
from datetime import UTC, datetime

import pytest
from app.db.models import Lead, LeadActivity, LeadFollowUp, LeadStatusHistory
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _lead_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "lead_number": f"LEAD-{suffix}",
        "lead_type": "general_sales_enquiry",
        "display_name": "Test Lead",
        "source": "website",
    }
    base.update(overrides)
    return base


async def test_lead_rejects_invalid_lead_type(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs(lead_type="not_a_real_type"))
    db_session.add(lead)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_rejects_invalid_source(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs(source="not_a_real_source"))
    db_session.add(lead)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_rejects_invalid_status(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs(status="not_a_real_status"))
    db_session.add(lead)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_rejects_invalid_priority(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs(priority="bogus"))
    db_session.add(lead)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_rejects_invalid_lost_reason(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs(lost_reason="not_a_real_reason"))
    db_session.add(lead)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_allows_null_lost_reason(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs())
    db_session.add(lead)
    await db_session.flush()
    assert lead.lost_reason is None


async def test_lead_defaults(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs())
    db_session.add(lead)
    await db_session.flush()

    assert lead.status == "new"
    assert lead.priority == "normal"
    assert lead.do_not_contact is False
    assert lead.won_customer_id is None
    assert lead.converted_at is None


async def test_lead_number_is_unique(db_session: AsyncSession) -> None:
    number = f"LEAD-{uuid.uuid4().hex[:10]}"
    db_session.add(Lead(**_lead_kwargs(lead_number=number)))
    await db_session.flush()

    db_session.add(Lead(**_lead_kwargs(lead_number=number)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_conversion_idempotency_key_is_unique(db_session: AsyncSession) -> None:
    """Regression test for the conversion idempotency guarantee: two
    different leads can never share the same conversion_idempotency_key,
    which is what makes `execute_conversion` safe to retry."""
    key = f"convert-{uuid.uuid4()}"
    db_session.add(Lead(**_lead_kwargs(conversion_idempotency_key=key)))
    await db_session.flush()

    db_session.add(Lead(**_lead_kwargs(conversion_idempotency_key=key)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_conversion_idempotency_key_null_does_not_conflict(
    db_session: AsyncSession,
) -> None:
    """The partial unique index only applies when the key is set — two
    unconverted leads (both NULL) must be allowed to coexist."""
    db_session.add(Lead(**_lead_kwargs()))
    db_session.add(Lead(**_lead_kwargs()))
    await db_session.flush()


async def test_lead_activity_rejects_invalid_activity_type(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs())
    db_session.add(lead)
    await db_session.flush()

    activity = LeadActivity(
        id=uuid.uuid4(),
        lead_id=lead.id,
        activity_type="not_a_real_type",
        summary="Called the customer.",
        occurred_at=datetime.now(UTC),
    )
    db_session.add(activity)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_activity_metadata_maps_to_reserved_column_name(
    db_session: AsyncSession,
) -> None:
    """Regression test: `activity_metadata` is the Python attribute name
    (SQLAlchemy reserves `metadata`) but must still read/write the real
    `metadata` database column."""
    lead = Lead(**_lead_kwargs())
    db_session.add(lead)
    await db_session.flush()

    activity = LeadActivity(
        id=uuid.uuid4(),
        lead_id=lead.id,
        activity_type="call",
        summary="Discussed pricing.",
        activity_metadata={"duration_seconds": 180},
        occurred_at=datetime.now(UTC),
    )
    db_session.add(activity)
    await db_session.flush()
    await db_session.refresh(activity)
    assert activity.activity_metadata == {"duration_seconds": 180}


async def test_lead_follow_up_rejects_invalid_status(
    db_session: AsyncSession,
) -> None:
    lead = Lead(**_lead_kwargs())
    db_session.add(lead)
    await db_session.flush()

    follow_up = LeadFollowUp(
        id=uuid.uuid4(),
        lead_id=lead.id,
        assigned_to=uuid.uuid4(),
        scheduled_at=datetime.now(UTC),
        status="not_a_real_status",
    )
    db_session.add(follow_up)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_follow_up_assigned_to_references_real_staff_user(
    db_session: AsyncSession,
) -> None:
    lead = Lead(**_lead_kwargs())
    db_session.add(lead)
    await db_session.flush()

    follow_up = LeadFollowUp(
        id=uuid.uuid4(),
        lead_id=lead.id,
        assigned_to=uuid.uuid4(),
        scheduled_at=datetime.now(UTC),
    )
    db_session.add(follow_up)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_lead_status_history_allows_null_previous_status(
    db_session: AsyncSession,
) -> None:
    """The first history row for a newly created lead has no
    previous_status — this is the row `create_lead` writes."""
    lead = Lead(**_lead_kwargs())
    db_session.add(lead)
    await db_session.flush()

    history = LeadStatusHistory(
        id=uuid.uuid4(),
        lead_id=lead.id,
        previous_status=None,
        new_status="new",
    )
    db_session.add(history)
    await db_session.flush()
    assert history.previous_status is None


async def test_lead_won_customer_id_references_real_customer(db_session: AsyncSession) -> None:
    lead = Lead(**_lead_kwargs(won_customer_id=uuid.uuid4()))
    db_session.add(lead)
    with pytest.raises(IntegrityError):
        await db_session.flush()
