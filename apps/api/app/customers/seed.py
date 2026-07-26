"""Idempotent development seed data for customers —
CORE_CRM_MODULES.md section 4.16 ("Dummy customer fixtures"),
PROJECT_PLAN.md section 5.

Only identity, preference, and tag fields from the canonical fixtures are
seeded. Order-derived fields (completed_order_count, lifetime_value_minor,
loyalty points, favorite product) are deliberately left at their honest
zero/NULL defaults — Phase 5 has no order or loyalty data to derive them
from, and this phase's own instruction is explicit: "never manually type
fake order totals into customer profiles." The canonical fixtures'
narrative numbers (12 completed orders, 680 loyalty points, etc.) describe
the *eventual* state once Phase 7/12 exist, not something to fabricate now.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.customers.schemas import CustomerAddressIn
from app.customers.service import add_address, add_note, add_tag, generate_customer_number
from app.db.models import Customer, StaffUser


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    stmt = select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    result = await session.scalar(stmt)
    return result


async def _get_or_create_customer(
    session: AsyncSession, *, email: str, actor: StaffUser | None, **fields: object
) -> tuple[Customer, bool]:
    existing = await session.scalar(select(Customer).where(Customer.primary_email == email))
    if existing is not None:
        return existing, False

    customer = Customer(
        id=uuid.uuid4(),
        customer_number=generate_customer_number(),
        primary_email=email,
        created_by=actor.id if actor else None,
        **fields,
    )
    session.add(customer)
    await session.flush()
    return customer, True


async def seed_customers(session: AsyncSession) -> None:
    actor = await _system_actor(session)

    ananya, created = await _get_or_create_customer(
        session,
        email="ananya.rao@example.test",
        actor=actor,
        customer_type="individual",
        first_name="Ananya",
        last_name="Rao",
        display_name="Ananya Rao",
        primary_phone_e164="+919876500001",
        dietary_preference="vegetarian",
        customer_status="active",
        customer_segment="new",
        acquisition_source="website",
    )
    if created and actor:
        await add_tag(session, actor=actor, customer=ananya, tag_name="Vegetarian", request=None)
        await add_note(
            session,
            actor=actor,
            customer=ananya,
            note_type="dietary",
            content="Prefers Paneer Tikka Pizza when available (Phase 6 menu reference fixture).",
            is_sensitive=False,
            request=None,
        )
        await add_address(
            session,
            actor=actor,
            customer=ananya,
            payload=CustomerAddressIn(
                label="Home",
                address_line1="12 MG Road",
                city="Bengaluru",
                state="Karnataka",
                postal_code="560001",
                is_default=True,
            ),
            request=None,
        )

    rahul, created = await _get_or_create_customer(
        session,
        email="rahul.mehta@example.test",
        actor=actor,
        customer_type="individual",
        first_name="Rahul",
        last_name="Mehta",
        display_name="Rahul Mehta",
        primary_phone_e164="+919876500002",
        dietary_preference="non_vegetarian",
        customer_status="active",
        customer_segment="at_risk",
    )
    if created and actor:
        await add_tag(session, actor=actor, customer=rahul, tag_name="At Risk", request=None)

    shreya, created = await _get_or_create_customer(
        session,
        email="shreya.kulkarni@example.test",
        actor=actor,
        customer_type="individual",
        first_name="Shreya",
        last_name="Kulkarni",
        display_name="Shreya Kulkarni",
        primary_phone_e164="+919876500003",
        dietary_preference="jain",
        customer_status="active",
        customer_segment="new",
    )
    if created and actor:
        await add_tag(session, actor=actor, customer=shreya, tag_name="Jain", request=None)

    await _get_or_create_customer(
        session,
        email="accounts@brightwave.example.test",
        actor=actor,
        customer_type="corporate",
        organization_name="BrightWave Technologies",
        display_name="BrightWave Technologies",
        primary_phone_e164="+919876500004",
        customer_status="active",
        customer_segment="corporate",
        acquisition_source="referral",
    )

    # Extra records so pagination and status/segment filters have enough
    # variety to actually exercise in the UI.
    await _get_or_create_customer(
        session,
        email="priya.sharma@example.test",
        actor=actor,
        customer_type="individual",
        first_name="Priya",
        last_name="Sharma",
        display_name="Priya Sharma",
        primary_phone_e164="+919876500005",
        customer_status="active",
        customer_segment="new",
    )
    await _get_or_create_customer(
        session,
        email="karthik.iyer@example.test",
        actor=actor,
        customer_type="individual",
        first_name="Karthik",
        last_name="Iyer",
        display_name="Karthik Iyer",
        primary_phone_e164="+919876500006",
        customer_status="inactive",
        customer_segment="dormant",
    )
    await _get_or_create_customer(
        session,
        email="blocked.customer@example.test",
        actor=actor,
        customer_type="individual",
        first_name="Blocked",
        last_name="Customer",
        display_name="Blocked Customer",
        customer_status="blacklisted",
    )
    await _get_or_create_customer(
        session,
        email="archived.customer@example.test",
        actor=actor,
        customer_type="individual",
        first_name="Archived",
        last_name="Customer",
        display_name="Archived Customer",
        customer_status="archived",
    )
