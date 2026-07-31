"""Offer configuration CRUD, versioning, and status lifecycle —
GROWTH_AND_INTELLIGENCE.md section 6.3/6.4/6.8. Editing an offer's rule
creates a new immutable `OfferVersion` rather than mutating history — see
`Offer`'s own docstring for the KnowledgeArticle/KnowledgeArticleVersion
precedent this mirrors.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.audit.service import record_audit_event
from app.db.models import Offer, OfferVersion, StaffUser
from app.offers.benefit import validate_benefit_kind_for_offer_type
from app.offers.errors import DuplicateOfferCodeError, InvalidStatusTransitionError
from app.offers.schemas import (
    OfferCreateIn,
    OfferStatus,
    OfferUpdateIn,
    OfferVersionCreateIn,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_OFFER_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"in_review", "cancelled"},
    "in_review": {"approved", "draft", "cancelled"},
    "approved": {"active", "cancelled"},
    "active": {"paused", "expired", "cancelled", "archived"},
    "paused": {"active", "cancelled", "archived"},
    "expired": {"archived"},
    "cancelled": {"archived"},
    "archived": set(),
}


async def list_offers(
    session: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    offer_type: str | None = None,
) -> tuple[list[Offer], int]:
    query = select(Offer)
    count_query = select(func.count()).select_from(Offer)
    if status is not None:
        query = query.where(Offer.status == status)
        count_query = count_query.where(Offer.status == status)
    if offer_type is not None:
        query = query.where(Offer.offer_type == offer_type)
        count_query = count_query.where(Offer.offer_type == offer_type)

    total = await session.scalar(count_query)
    rows = await session.scalars(
        query.order_by(Offer.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    return list(rows), total or 0


async def get_offer(session: AsyncSession, offer_id: uuid.UUID) -> Offer | None:
    return await session.get(Offer, offer_id)


async def get_offer_by_code(session: AsyncSession, code: str) -> Offer | None:
    result: Offer | None = await session.scalar(select(Offer).where(Offer.offer_code == code))
    return result


async def get_latest_version(session: AsyncSession, offer: Offer) -> OfferVersion:
    if offer.latest_version_id is None:
        raise InvalidStatusTransitionError(f"Offer {offer.offer_code!r} has no version yet.")
    version = await session.get(OfferVersion, offer.latest_version_id)
    if version is None:
        raise InvalidStatusTransitionError(
            f"Offer {offer.offer_code!r}'s latest version is missing."
        )
    return version


async def _create_version(
    session: AsyncSession, *, offer: Offer, payload: OfferVersionCreateIn, actor: StaffUser | None
) -> OfferVersion:
    version = OfferVersion(
        id=uuid.uuid4(),
        offer_id=offer.id,
        version_number=offer.latest_version_number,
        eligibility_rule=payload.eligibility_rule.model_dump(mode="json"),
        benefit_rule=payload.benefit_rule.model_dump(mode="json"),
        minimum_order_value_minor=payload.minimum_order_value_minor,
        maximum_discount_minor=payload.maximum_discount_minor,
        applicable_product_ids=payload.applicable_product_ids,
        excluded_product_ids=payload.excluded_product_ids,
        applicable_category_ids=payload.applicable_category_ids,
        channel_eligibility=payload.channel_eligibility,
        day_time_windows=payload.day_time_windows,
        global_usage_limit=payload.global_usage_limit,
        per_customer_usage_limit=payload.per_customer_usage_limit,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
        created_by=actor.id if actor else None,
        created_at=datetime.now(UTC),
    )
    session.add(version)
    await session.flush()
    return version


async def create_offer(session: AsyncSession, *, actor: StaffUser, payload: OfferCreateIn) -> Offer:
    validate_benefit_kind_for_offer_type(payload.offer_type, payload.initial_version.benefit_rule)

    existing = await get_offer_by_code(session, payload.offer_code)
    if existing is not None:
        raise DuplicateOfferCodeError(f"Offer code {payload.offer_code!r} is already in use.")

    offer = Offer(
        id=uuid.uuid4(),
        offer_code=payload.offer_code,
        internal_name=payload.internal_name,
        customer_facing_name=payload.customer_facing_name,
        offer_type=payload.offer_type,
        status="draft",
        requires_code=payload.requires_code,
        stackability_group=payload.stackability_group,
        is_exclusive=payload.is_exclusive,
        budget_cap_minor=payload.budget_cap_minor,
        redemption_cap=payload.redemption_cap,
        redemption_count=0,
        requires_approval=payload.requires_approval,
        financial_owner_id=payload.financial_owner_id,
        terms_and_notes=payload.terms_and_notes,
        latest_version_number=1,
        created_by=actor.id,
        updated_by=actor.id,
    )
    session.add(offer)
    await session.flush()

    version = await _create_version(
        session, offer=offer, payload=payload.initial_version, actor=actor
    )
    offer.latest_version_id = version.id
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="offer.created",
        target_type="offer",
        target_id=offer.id,
        safe_metadata={"offer_code": offer.offer_code, "offer_type": offer.offer_type},
    )
    return offer


async def create_new_version(
    session: AsyncSession, *, actor: StaffUser, offer: Offer, payload: OfferVersionCreateIn
) -> OfferVersion:
    validate_benefit_kind_for_offer_type(offer.offer_type, payload.benefit_rule)

    offer.latest_version_number += 1
    version = await _create_version(session, offer=offer, payload=payload, actor=actor)
    offer.latest_version_id = version.id
    offer.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="offer.version_created",
        target_type="offer",
        target_id=offer.id,
        safe_metadata={"version_number": version.version_number},
    )
    return version


async def update_offer(
    session: AsyncSession, *, actor: StaffUser, offer: Offer, payload: OfferUpdateIn
) -> Offer:
    if payload.internal_name is not None:
        offer.internal_name = payload.internal_name
    if payload.customer_facing_name is not None:
        offer.customer_facing_name = payload.customer_facing_name
    if payload.stackability_group is not None:
        offer.stackability_group = payload.stackability_group
    if payload.is_exclusive is not None:
        offer.is_exclusive = payload.is_exclusive
    if payload.budget_cap_minor is not None:
        offer.budget_cap_minor = payload.budget_cap_minor
    if payload.redemption_cap is not None:
        offer.redemption_cap = payload.redemption_cap
    if payload.financial_owner_id is not None:
        offer.financial_owner_id = payload.financial_owner_id
    if payload.terms_and_notes is not None:
        offer.terms_and_notes = payload.terms_and_notes
    offer.updated_by = actor.id
    await session.flush()
    return offer


async def transition_offer(
    session: AsyncSession, *, actor: StaffUser, offer: Offer, target_status: OfferStatus
) -> Offer:
    allowed = _OFFER_TRANSITIONS.get(offer.status, set())
    if target_status not in allowed:
        raise InvalidStatusTransitionError(
            f"Cannot transition offer from {offer.status!r} to {target_status!r}."
        )
    if target_status == "approved":
        offer.approved_by = actor.id
        offer.approved_at = datetime.now(UTC)
    if target_status == "archived":
        offer.archived_at = datetime.now(UTC)

    offer.status = target_status
    offer.updated_by = actor.id
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="offer.transitioned",
        target_type="offer",
        target_id=offer.id,
        safe_metadata={"target_status": target_status},
    )
    return offer
