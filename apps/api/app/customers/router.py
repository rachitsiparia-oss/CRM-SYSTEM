import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.customers import service
from app.customers.schemas import (
    CustomerAddressIn,
    CustomerAddressOut,
    CustomerArchiveIn,
    CustomerAssignIn,
    CustomerConsentOut,
    CustomerConsentSetIn,
    CustomerCreateIn,
    CustomerListItemOut,
    CustomerNoteIn,
    CustomerNoteOut,
    CustomerNoteUpdateIn,
    CustomerOut,
    CustomerTagAddIn,
    CustomerUpdateIn,
    DuplicateMatchOut,
    MergeExecuteIn,
    MergePreviewOut,
    TagOut,
    TimelineEntryOut,
)
from app.db.models import (
    AuditEvent,
    Customer,
    CustomerAddress,
    CustomerNote,
    CustomerTag,
    StaffUser,
    Tag,
)
from app.db.session import get_db
from app.permissions.dependencies import require_permission
from app.permissions.service import has_permission
from app.shared.normalization import NormalizationError, normalize_email, normalize_phone

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])

_SORT_ALLOWLIST = {"display_name", "created_at", "last_order_at", "lifetime_value_minor"}


async def _get_customer_or_404(session: AsyncSession, customer_id: uuid.UUID) -> Customer:
    customer = await session.scalar(
        select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None))
    )
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    return customer


@router.get("")
async def list_customers(
    request: Request,
    _actor: StaffUser = Depends(require_permission("customers.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
    customer_status: str | None = Query(default=None),
    customer_segment: str | None = Query(default=None),
    customer_type: str | None = Query(default=None),
    assigned_staff_id: uuid.UUID | None = Query(default=None),
    sort: str = Query(default="created_at"),
) -> PaginatedResponse[CustomerListItemOut]:
    if sort not in _SORT_ALLOWLIST:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort column."
        )

    stmt = select(Customer).where(Customer.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(Customer).where(Customer.deleted_at.is_(None))

    if not customer_status:
        stmt = stmt.where(Customer.customer_status != "merged")
        count_stmt = count_stmt.where(Customer.customer_status != "merged")

    if search:
        pattern = f"%{search}%"
        clause = or_(
            Customer.display_name.ilike(pattern),
            Customer.customer_number.ilike(pattern),
            Customer.primary_phone_e164.ilike(pattern),
            Customer.primary_email.ilike(pattern),
        )
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if customer_status:
        stmt = stmt.where(Customer.customer_status == customer_status)
        count_stmt = count_stmt.where(Customer.customer_status == customer_status)
    if customer_segment:
        stmt = stmt.where(Customer.customer_segment == customer_segment)
        count_stmt = count_stmt.where(Customer.customer_segment == customer_segment)
    if customer_type:
        stmt = stmt.where(Customer.customer_type == customer_type)
        count_stmt = count_stmt.where(Customer.customer_type == customer_type)
    if assigned_staff_id:
        stmt = stmt.where(Customer.assigned_staff_id == assigned_staff_id)
        count_stmt = count_stmt.where(Customer.assigned_staff_id == assigned_staff_id)

    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(getattr(Customer, sort).desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    data = [CustomerListItemOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/duplicates")
async def check_duplicates(
    request: Request,
    _actor: StaffUser = Depends(require_permission("customers.view")),
    session: AsyncSession = Depends(get_db),
    phone: str | None = Query(default=None),
    email: str | None = Query(default=None),
    exclude_customer_id: uuid.UUID | None = Query(default=None),
) -> DataResponse[list[DuplicateMatchOut]]:
    try:
        normalized_phone = normalize_phone(phone)
        normalized_email = normalize_email(email)
    except NormalizationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    matches = await service.find_duplicate_customers(
        session, phone=normalized_phone, email=normalized_email, exclude_id=exclude_customer_id
    )
    data = [
        DuplicateMatchOut(
            customer=CustomerListItemOut.model_validate(customer), match_reasons=reasons
        )
        for customer, reasons in matches
    ]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_customer(
    request: Request,
    payload: CustomerCreateIn,
    actor: StaffUser = Depends(require_permission("customers.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerOut]:
    customer = await service.create_customer(session, actor=actor, payload=payload, request=request)
    return DataResponse(data=CustomerOut.model_validate(customer), meta=request_meta(request))


@router.get("/{customer_id}")
async def get_customer(
    request: Request,
    customer_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("customers.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerOut]:
    customer = await _get_customer_or_404(session, customer_id)
    return DataResponse(data=CustomerOut.model_validate(customer), meta=request_meta(request))


@router.patch("/{customer_id}")
async def update_customer(
    request: Request,
    customer_id: uuid.UUID,
    payload: CustomerUpdateIn,
    actor: StaffUser = Depends(require_permission("customers.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerOut]:
    customer = await _get_customer_or_404(session, customer_id)
    customer = await service.update_customer(
        session, actor=actor, customer=customer, payload=payload, request=request
    )
    return DataResponse(data=CustomerOut.model_validate(customer), meta=request_meta(request))


@router.delete("/{customer_id}")
async def archive_customer(
    request: Request,
    customer_id: uuid.UUID,
    payload: CustomerArchiveIn,
    actor: StaffUser = Depends(require_permission("customers.archive")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerOut]:
    customer = await _get_customer_or_404(session, customer_id)
    await service.set_customer_status(
        session,
        actor=actor,
        customer=customer,
        new_status="archived",
        reason=payload.reason,
        request=request,
    )
    return DataResponse(data=CustomerOut.model_validate(customer), meta=request_meta(request))


@router.post("/{customer_id}/restore")
async def restore_customer(
    request: Request,
    customer_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("customers.restore")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerOut]:
    customer = await _get_customer_or_404(session, customer_id)
    await service.set_customer_status(
        session,
        actor=actor,
        customer=customer,
        new_status="active",
        reason="restored",
        request=request,
    )
    return DataResponse(data=CustomerOut.model_validate(customer), meta=request_meta(request))


@router.post("/{customer_id}/assign")
async def assign_customer(
    request: Request,
    customer_id: uuid.UUID,
    payload: CustomerAssignIn,
    actor: StaffUser = Depends(require_permission("customers.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerOut]:
    customer = await _get_customer_or_404(session, customer_id)
    await service.assign_customer(
        session,
        actor=actor,
        customer=customer,
        assigned_staff_id=payload.assigned_staff_id,
        request=request,
    )
    return DataResponse(data=CustomerOut.model_validate(customer), meta=request_meta(request))


@router.get("/{customer_id}/timeline")
async def get_customer_timeline(
    request: Request,
    customer_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("customers.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
) -> PaginatedResponse[TimelineEntryOut]:
    await _get_customer_or_404(session, customer_id)
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.target_type == "customer", AuditEvent.target_id == customer_id)
        .order_by(AuditEvent.created_at.desc())
    )
    count_stmt = (
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.target_type == "customer", AuditEvent.target_id == customer_id)
    )
    total = await session.scalar(count_stmt) or 0
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [TimelineEntryOut.model_validate(row, from_attributes=True) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/{customer_id}/addresses")
async def list_addresses(
    request: Request,
    customer_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("customers.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[CustomerAddressOut]]:
    await _get_customer_or_404(session, customer_id)
    rows = (
        await session.scalars(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer_id, CustomerAddress.deleted_at.is_(None))
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at)
        )
    ).all()
    data = [CustomerAddressOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/{customer_id}/addresses", status_code=status.HTTP_201_CREATED)
async def add_address(
    request: Request,
    customer_id: uuid.UUID,
    payload: CustomerAddressIn,
    actor: StaffUser = Depends(require_permission("customers.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerAddressOut]:
    customer = await _get_customer_or_404(session, customer_id)
    address = await service.add_address(
        session, actor=actor, customer=customer, payload=payload, request=request
    )
    return DataResponse(data=CustomerAddressOut.model_validate(address), meta=request_meta(request))


async def _get_address_or_404(
    session: AsyncSession, customer_id: uuid.UUID, address_id: uuid.UUID
) -> CustomerAddress:
    address = await session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.deleted_at.is_(None),
        )
    )
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")
    return address


@router.patch("/{customer_id}/addresses/{address_id}")
async def update_address(
    request: Request,
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    payload: CustomerAddressIn,
    actor: StaffUser = Depends(require_permission("customers.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerAddressOut]:
    customer = await _get_customer_or_404(session, customer_id)
    address = await _get_address_or_404(session, customer_id, address_id)
    address = await service.update_address(
        session, actor=actor, customer=customer, address=address, payload=payload, request=request
    )
    return DataResponse(data=CustomerAddressOut.model_validate(address), meta=request_meta(request))


@router.delete("/{customer_id}/addresses/{address_id}")
async def archive_address(
    request: Request,
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("customers.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    customer = await _get_customer_or_404(session, customer_id)
    address = await _get_address_or_404(session, customer_id, address_id)
    await service.archive_address(
        session, actor=actor, customer=customer, address=address, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/{customer_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_note(
    request: Request,
    customer_id: uuid.UUID,
    payload: CustomerNoteIn,
    actor: StaffUser = Depends(require_permission("customers.notes.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerNoteOut]:
    customer = await _get_customer_or_404(session, customer_id)
    note = await service.add_note(
        session,
        actor=actor,
        customer=customer,
        note_type=payload.note_type,
        content=payload.content,
        is_sensitive=payload.is_sensitive,
        request=request,
    )
    return DataResponse(data=CustomerNoteOut.model_validate(note), meta=request_meta(request))


@router.get("/{customer_id}/notes")
async def list_notes(
    request: Request,
    customer_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("customers.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[CustomerNoteOut]]:
    await _get_customer_or_404(session, customer_id)
    can_read_sensitive = await has_permission(session, actor.id, "customers.notes.sensitive.read")

    stmt = select(CustomerNote).where(
        CustomerNote.customer_id == customer_id, CustomerNote.deleted_at.is_(None)
    )
    if not can_read_sensitive:
        stmt = stmt.where(CustomerNote.is_sensitive.is_(False))
    stmt = stmt.order_by(CustomerNote.created_at.desc())
    rows = (await session.scalars(stmt)).all()
    data = [CustomerNoteOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.patch("/{customer_id}/notes/{note_id}")
async def update_note(
    request: Request,
    customer_id: uuid.UUID,
    note_id: uuid.UUID,
    payload: CustomerNoteUpdateIn,
    actor: StaffUser = Depends(require_permission("customers.notes.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerNoteOut]:
    customer = await _get_customer_or_404(session, customer_id)
    note = await session.scalar(
        select(CustomerNote).where(
            CustomerNote.id == note_id,
            CustomerNote.customer_id == customer_id,
            CustomerNote.deleted_at.is_(None),
        )
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    note = await service.update_note(
        session, actor=actor, customer=customer, note=note, content=payload.content, request=request
    )
    return DataResponse(data=CustomerNoteOut.model_validate(note), meta=request_meta(request))


@router.post("/{customer_id}/tags", status_code=status.HTTP_201_CREATED)
async def add_tag(
    request: Request,
    customer_id: uuid.UUID,
    payload: CustomerTagAddIn,
    actor: StaffUser = Depends(require_permission("customers.tags.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TagOut]:
    customer = await _get_customer_or_404(session, customer_id)
    tag = await service.add_tag(
        session, actor=actor, customer=customer, tag_name=payload.name, request=request
    )
    return DataResponse(data=TagOut.model_validate(tag), meta=request_meta(request))


@router.get("/{customer_id}/tags")
async def list_tags(
    request: Request,
    customer_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("customers.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TagOut]]:
    await _get_customer_or_404(session, customer_id)
    rows = (
        await session.scalars(
            select(Tag)
            .join(CustomerTag, CustomerTag.tag_id == Tag.id)
            .where(CustomerTag.customer_id == customer_id)
        )
    ).all()
    data = [TagOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.delete("/{customer_id}/tags/{tag_id}")
async def remove_tag(
    request: Request,
    customer_id: uuid.UUID,
    tag_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("customers.tags.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    customer = await _get_customer_or_404(session, customer_id)
    await service.remove_tag(
        session, actor=actor, customer=customer, tag_id=tag_id, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.put("/{customer_id}/consents/{consent_type}")
async def set_consent(
    request: Request,
    customer_id: uuid.UUID,
    consent_type: str,
    payload: CustomerConsentSetIn,
    actor: StaffUser = Depends(require_permission("customers.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerConsentOut]:
    customer = await _get_customer_or_404(session, customer_id)
    consent = await service.set_consent(
        session,
        actor=actor,
        customer=customer,
        consent_type=consent_type,
        status_value=payload.status,
        source=payload.source,
        policy_version=payload.policy_version,
        captured_text=payload.captured_text,
        request=request,
    )
    return DataResponse(data=CustomerConsentOut.model_validate(consent), meta=request_meta(request))


@router.post("/merge/preview")
async def preview_merge(
    request: Request,
    source_customer_id: uuid.UUID = Query(...),
    surviving_customer_id: uuid.UUID = Query(...),
    _actor: StaffUser = Depends(require_permission("customers.merge")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[MergePreviewOut]:
    source = await _get_customer_or_404(session, source_customer_id)
    surviving = await _get_customer_or_404(session, surviving_customer_id)
    result = await service.preview_merge(session, source=source, surviving=surviving)
    out = MergePreviewOut(
        source=CustomerOut.model_validate(source),
        surviving=CustomerOut.model_validate(surviving),
        **result,
    )
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/merge")
async def execute_merge(
    request: Request,
    payload: MergeExecuteIn,
    actor: StaffUser = Depends(require_permission("customers.merge")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerOut]:
    source = await _get_customer_or_404(session, payload.source_customer_id)
    surviving = await _get_customer_or_404(session, payload.surviving_customer_id)
    surviving = await service.execute_merge(
        session,
        actor=actor,
        source=source,
        surviving=surviving,
        reason=payload.reason,
        field_resolutions=payload.field_resolutions,
        request=request,
    )
    return DataResponse(data=CustomerOut.model_validate(surviving), meta=request_meta(request))
