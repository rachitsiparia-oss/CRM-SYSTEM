"""Customer business logic — CORE_CRM_MODULES.md section 4, DATABASE_AND_API.md
section 6.

Kept out of the router so duplicate-detection and merge behavior are
unit-testable without an HTTP client, matching the app.staff.service
pattern from Phase 3.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.customers.schemas import (
    CustomerAddressIn,
    CustomerCreateIn,
    CustomerUpdateIn,
    MergeFieldResolution,
)
from app.db.models import (
    Customer,
    CustomerAddress,
    CustomerConsent,
    CustomerMergeEvent,
    CustomerNote,
    CustomerTag,
    StaffUser,
    Tag,
)
from app.outbox.service import record_domain_event
from app.shared.normalization import normalize_tag_name

# Fields eligible for conflict resolution during a merge — identity/profile
# fields only. Metrics (lifetime_value_minor etc.) are never merged here
# since Phase 5 has no order data to reconcile; they stay at the surviving
# record's own (zero/NULL) values.
_MERGEABLE_FIELDS = (
    "first_name",
    "last_name",
    "organization_name",
    "display_name",
    "primary_phone_e164",
    "primary_email",
    "date_of_birth",
    "anniversary_date",
    "preferred_language",
    "dietary_preference",
    "spice_preference",
    "customer_segment",
    "acquisition_source",
    "assigned_staff_id",
)


def generate_customer_number() -> str:
    return f"CUST-{uuid.uuid4().hex[:8].upper()}"


def derive_display_name(
    *,
    display_name: str | None,
    first_name: str | None,
    last_name: str | None,
    organization_name: str | None,
) -> str:
    if display_name and display_name.strip():
        return display_name.strip()
    if organization_name and organization_name.strip():
        return organization_name.strip()
    name = " ".join(part for part in (first_name, last_name) if part and part.strip())
    if name:
        return name
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide a display name, organization name, or first/last name.",
    )


async def find_duplicate_customers(
    session: AsyncSession,
    *,
    phone: str | None,
    email: str | None,
    exclude_id: uuid.UUID | None = None,
) -> list[tuple[Customer, list[str]]]:
    """Deterministic duplicate detection — CORE_CRM_MODULES.md section 4.7.
    Matches on exact normalized phone or exact normalized email only; no
    fuzzy name matching, per this phase's own instruction to start with
    deterministic matching."""
    if not phone and not email:
        return []

    conditions = []
    if phone:
        conditions.append(Customer.primary_phone_e164 == phone)
    if email:
        conditions.append(Customer.primary_email == email)

    stmt = select(Customer).where(or_(*conditions), Customer.deleted_at.is_(None))
    if exclude_id is not None:
        stmt = stmt.where(Customer.id != exclude_id)

    candidates = (await session.scalars(stmt)).all()
    results: list[tuple[Customer, list[str]]] = []
    for candidate in candidates:
        reasons = []
        if phone and candidate.primary_phone_e164 == phone:
            reasons.append("exact_normalized_phone")
        if email and candidate.primary_email == email:
            reasons.append("exact_normalized_email")
        results.append((candidate, reasons))
    return results


async def create_customer(
    session: AsyncSession, *, actor: StaffUser, payload: CustomerCreateIn, request: Request | None
) -> Customer:
    display_name = derive_display_name(
        display_name=payload.display_name,
        first_name=payload.first_name,
        last_name=payload.last_name,
        organization_name=payload.organization_name,
    )

    customer = Customer(
        id=uuid.uuid4(),
        customer_number=generate_customer_number(),
        customer_type=payload.customer_type,
        first_name=payload.first_name,
        last_name=payload.last_name,
        organization_name=payload.organization_name,
        display_name=display_name,
        primary_phone_e164=payload.primary_phone_e164,
        primary_email=payload.primary_email,
        date_of_birth=payload.date_of_birth,
        anniversary_date=payload.anniversary_date,
        preferred_language=payload.preferred_language,
        dietary_preference=payload.dietary_preference,
        spice_preference=payload.spice_preference,
        customer_status="active",
        customer_segment=payload.customer_segment or "new",
        acquisition_source=payload.acquisition_source,
        assigned_staff_id=payload.assigned_staff_id,
        created_by=actor.id,
        last_activity_at=datetime.now(UTC),
    )
    session.add(customer)
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.created",
        target_type="customer",
        target_id=customer.id,
        request=request,
        safe_metadata={"customer_number": customer.customer_number},
    )
    await record_domain_event(
        session,
        event_type="customer.created",
        aggregate_type="customer",
        aggregate_id=customer.id,
        payload={"customer_id": str(customer.id), "customer_number": customer.customer_number},
    )
    return customer


async def update_customer(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    payload: CustomerUpdateIn,
    request: Request | None,
) -> Customer:
    if payload.expected_version is not None and payload.expected_version != customer.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This customer was updated by someone else. Reload and try again.",
        )

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = {field: getattr(customer, field) for field in updates}
    for field, value in updates.items():
        setattr(customer, field, value)
    if not customer.display_name:
        customer.display_name = derive_display_name(
            display_name=None,
            first_name=customer.first_name,
            last_name=customer.last_name,
            organization_name=customer.organization_name,
        )

    if updates:
        customer.version += 1
        customer.updated_by = actor.id
        customer.last_activity_at = datetime.now(UTC)
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="customer.updated",
            target_type="customer",
            target_id=customer.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
        await record_domain_event(
            session,
            event_type="customer.updated",
            aggregate_type="customer",
            aggregate_id=customer.id,
            payload={"customer_id": str(customer.id), "fields": sorted(updates.keys())},
        )
    return customer


async def assign_customer(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    assigned_staff_id: uuid.UUID | None,
    request: Request | None,
) -> None:
    before = customer.assigned_staff_id
    customer.assigned_staff_id = assigned_staff_id
    customer.updated_by = actor.id
    customer.version += 1
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.assigned",
        target_type="customer",
        target_id=customer.id,
        request=request,
        before_summary={"assigned_staff_id": str(before) if before else None},
        after_summary={"assigned_staff_id": str(assigned_staff_id) if assigned_staff_id else None},
    )


async def set_customer_status(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    new_status: str,
    reason: str,
    request: Request | None,
) -> None:
    before_status = customer.customer_status
    customer.customer_status = new_status
    customer.updated_by = actor.id
    customer.version += 1
    action_code = "customer.archived" if new_status == "archived" else "customer.restored"
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code=action_code,
        target_type="customer",
        target_id=customer.id,
        request=request,
        before_summary={"customer_status": before_status},
        after_summary={"customer_status": new_status},
        safe_metadata={"reason": reason},
    )


async def add_address(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    payload: CustomerAddressIn,
    request: Request | None,
) -> CustomerAddress:
    if payload.is_default:
        await _clear_default_address(session, customer_id=customer.id)

    address = CustomerAddress(
        id=uuid.uuid4(),
        customer_id=customer.id,
        label=payload.label,
        recipient_name=payload.recipient_name,
        phone_e164=payload.phone_e164,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        landmark=payload.landmark,
        locality=payload.locality,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
        latitude=payload.latitude,
        longitude=payload.longitude,
        delivery_instructions=payload.delivery_instructions,
        is_default=payload.is_default,
        created_by=actor.id,
    )
    session.add(address)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.address_added",
        target_type="customer",
        target_id=customer.id,
        request=request,
        safe_metadata={"address_id": str(address.id)},
    )
    return address


async def _clear_default_address(session: AsyncSession, *, customer_id: uuid.UUID) -> None:
    existing = (
        await session.scalars(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == customer_id,
                CustomerAddress.is_default.is_(True),
                CustomerAddress.deleted_at.is_(None),
            )
        )
    ).all()
    for address in existing:
        address.is_default = False


async def update_address(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    address: CustomerAddress,
    payload: CustomerAddressIn,
    request: Request | None,
) -> CustomerAddress:
    if payload.is_default and not address.is_default:
        await _clear_default_address(session, customer_id=customer.id)

    for field, value in payload.model_dump().items():
        setattr(address, field, value)
    address.updated_by = actor.id
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.address_changed",
        target_type="customer",
        target_id=customer.id,
        request=request,
        safe_metadata={"address_id": str(address.id)},
    )
    return address


async def archive_address(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    address: CustomerAddress,
    request: Request | None,
) -> None:
    address.deleted_at = datetime.now(UTC)
    address.deleted_by = actor.id
    address.is_active = False
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.address_changed",
        target_type="customer",
        target_id=customer.id,
        request=request,
        safe_metadata={"address_id": str(address.id), "action": "archived"},
    )


async def add_note(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    note_type: str,
    content: str,
    is_sensitive: bool,
    request: Request | None,
) -> CustomerNote:
    note = CustomerNote(
        id=uuid.uuid4(),
        customer_id=customer.id,
        note_type=note_type,
        content=content,
        is_sensitive=is_sensitive,
        created_by=actor.id,
    )
    session.add(note)
    customer.last_activity_at = datetime.now(UTC)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.note_changed",
        target_type="customer",
        target_id=customer.id,
        request=request,
        safe_metadata={"note_id": str(note.id), "action": "created"},
    )
    return note


async def update_note(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    note: CustomerNote,
    content: str,
    request: Request | None,
) -> CustomerNote:
    note.content = content
    note.updated_at = datetime.now(UTC)
    note.updated_by = actor.id
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.note_changed",
        target_type="customer",
        target_id=customer.id,
        request=request,
        safe_metadata={"note_id": str(note.id), "action": "edited"},
    )
    return note


async def add_tag(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    tag_name: str,
    request: Request | None,
) -> Tag:
    normalized = normalize_tag_name(tag_name)
    tag = await session.scalar(select(Tag).where(Tag.normalized_name == normalized))
    if tag is None:
        tag = Tag(id=uuid.uuid4(), name=tag_name.strip(), normalized_name=normalized)
        session.add(tag)
        await session.flush()

    existing_link = await session.scalar(
        select(CustomerTag).where(
            CustomerTag.customer_id == customer.id, CustomerTag.tag_id == tag.id
        )
    )
    if existing_link is None:
        session.add(CustomerTag(customer_id=customer.id, tag_id=tag.id, assigned_by=actor.id))
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="customer.tag_added",
            target_type="customer",
            target_id=customer.id,
            request=request,
            safe_metadata={"tag": normalized},
        )
    return tag


async def remove_tag(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    tag_id: uuid.UUID,
    request: Request | None,
) -> None:
    link = await session.scalar(
        select(CustomerTag).where(
            CustomerTag.customer_id == customer.id, CustomerTag.tag_id == tag_id
        )
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag is not assigned.")
    await session.delete(link)
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.tag_removed",
        target_type="customer",
        target_id=customer.id,
        request=request,
        safe_metadata={"tag_id": str(tag_id)},
    )


async def set_consent(
    session: AsyncSession,
    *,
    actor: StaffUser,
    customer: Customer,
    consent_type: str,
    status_value: str,
    source: str,
    policy_version: str | None,
    captured_text: str | None,
    request: Request | None,
) -> CustomerConsent:
    consent = await session.scalar(
        select(CustomerConsent).where(
            CustomerConsent.customer_id == customer.id, CustomerConsent.consent_type == consent_type
        )
    )
    now = datetime.now(UTC)
    if consent is None:
        consent = CustomerConsent(
            id=uuid.uuid4(),
            customer_id=customer.id,
            consent_type=consent_type,
            status=status_value,
            source=source,
        )
        session.add(consent)

    consent.status = status_value
    consent.source = source
    consent.policy_version = policy_version
    consent.captured_text = captured_text
    if status_value == "granted":
        consent.granted_at = now
        consent.withdrawn_at = None
    elif status_value == "withdrawn":
        consent.withdrawn_at = now

    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.consent_changed",
        target_type="customer",
        target_id=customer.id,
        request=request,
        safe_metadata={"consent_type": consent_type, "status": status_value},
    )
    return consent


async def preview_merge(
    session: AsyncSession, *, source: Customer, surviving: Customer
) -> dict[str, Any]:
    if source.id == surviving.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge a customer into itself."
        )
    if source.merged_into_customer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Source customer has already been merged."
        )
    if surviving.merged_into_customer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Surviving customer is itself a merged (non-canonical) record.",
        )

    conflicting = [
        field
        for field in _MERGEABLE_FIELDS
        if getattr(source, field) not in (None, "")
        and getattr(source, field) != getattr(surviving, field)
    ]
    address_count = await session.scalar(
        select(CustomerAddress.id).where(
            CustomerAddress.customer_id == source.id, CustomerAddress.deleted_at.is_(None)
        )
    )
    tag_count = len(
        (
            await session.scalars(select(CustomerTag).where(CustomerTag.customer_id == source.id))
        ).all()
    )
    note_count = len(
        (
            await session.scalars(select(CustomerNote).where(CustomerNote.customer_id == source.id))
        ).all()
    )
    return {
        "conflicting_fields": conflicting,
        "source_address_count": 1 if address_count else 0,
        "source_tag_count": tag_count,
        "source_note_count": note_count,
    }


async def execute_merge(
    session: AsyncSession,
    *,
    actor: StaffUser,
    source: Customer,
    surviving: Customer,
    reason: str,
    field_resolutions: list[MergeFieldResolution],
    request: Request | None,
) -> Customer:
    if source.id == surviving.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge a customer into itself."
        )
    if source.merged_into_customer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Source customer has already been merged."
        )
    if surviving.merged_into_customer_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Surviving customer is itself a merged (non-canonical) record.",
        )

    resolutions = {r.field: r.value for r in field_resolutions if r.field in _MERGEABLE_FIELDS}
    for field, value in resolutions.items():
        setattr(surviving, field, value)

    # Re-point every linked record — addresses, tags, notes, consents.
    addresses = (
        await session.scalars(
            select(CustomerAddress).where(CustomerAddress.customer_id == source.id)
        )
    ).all()
    for address in addresses:
        address.customer_id = surviving.id
        address.is_default = False

    source_tags = (
        await session.scalars(select(CustomerTag).where(CustomerTag.customer_id == source.id))
    ).all()
    surviving_tag_ids = {
        row.tag_id
        for row in (
            await session.scalars(
                select(CustomerTag).where(CustomerTag.customer_id == surviving.id)
            )
        ).all()
    }
    for tag_link in source_tags:
        if tag_link.tag_id in surviving_tag_ids:
            await session.delete(tag_link)
        else:
            tag_link.customer_id = surviving.id

    notes = (
        await session.scalars(select(CustomerNote).where(CustomerNote.customer_id == source.id))
    ).all()
    for note in notes:
        note.customer_id = surviving.id

    consents = (
        await session.scalars(
            select(CustomerConsent).where(CustomerConsent.customer_id == source.id)
        )
    ).all()
    surviving_consent_types = {
        row.consent_type
        for row in (
            await session.scalars(
                select(CustomerConsent).where(CustomerConsent.customer_id == surviving.id)
            )
        ).all()
    }
    for consent in consents:
        if consent.consent_type in surviving_consent_types:
            await session.delete(consent)
        else:
            consent.customer_id = surviving.id

    source.customer_status = "merged"
    source.merged_into_customer_id = surviving.id
    source.updated_by = actor.id
    surviving.updated_by = actor.id
    surviving.version += 1

    mapping_summary = {
        "addresses_moved": len(addresses),
        "tags_moved": len(source_tags),
        "notes_moved": len(notes),
        "consents_moved": len(consents),
        "fields_resolved": list(resolutions.keys()),
    }
    merge_event = CustomerMergeEvent(
        id=uuid.uuid4(),
        source_customer_id=source.id,
        surviving_customer_id=surviving.id,
        actor_id=actor.id,
        reason=reason,
        mapping_summary=mapping_summary,
    )
    session.add(merge_event)
    await session.flush()

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="customer.merged",
        target_type="customer",
        target_id=surviving.id,
        request=request,
        safe_metadata={"source_customer_id": str(source.id), "reason": reason, **mapping_summary},
    )
    await record_domain_event(
        session,
        event_type="customer.merged",
        aggregate_type="customer",
        aggregate_id=surviving.id,
        payload={"source_customer_id": str(source.id), "surviving_customer_id": str(surviving.id)},
    )
    return surviving
