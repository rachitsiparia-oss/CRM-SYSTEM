import uuid
from datetime import date, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import (
    BusinessHours,
    DiningArea,
    HolidayCalendar,
    Reservation,
    ReservationNote,
    ReservationPolicies,
    ReservationSettings,
    ReservationStatusHistory,
    ReservationTimeline,
    ReservationWaitlist,
    RestaurantTable,
    StaffUser,
    TableBlock,
    TableStatusHistory,
)
from app.db.session import get_db
from app.feedback import integrations as feedback_integrations
from app.permissions.dependencies import require_permission
from app.reservations import (
    assignment,
    availability,
    customer_stats,
    dashboard,
    order_link,
    service,
    tables,
    walkin,
)
from app.reservations import (
    settings as settings_service,
)
from app.reservations import (
    waitlist as waitlist_service,
)
from app.reservations.schemas import (
    ArchiveIn,
    BusinessHoursOut,
    BusinessHoursUpdateIn,
    CustomerReservationStatsOut,
    DiningAreaCreateIn,
    DiningAreaOut,
    DiningAreaUpdateIn,
    HolidayCalendarCreateIn,
    HolidayCalendarOut,
    HolidayCalendarUpdateIn,
    ReservationApprovalIn,
    ReservationCreateIn,
    ReservationDashboardStatsOut,
    ReservationNoteIn,
    ReservationNoteOut,
    ReservationOrderLinkIn,
    ReservationOut,
    ReservationPoliciesOut,
    ReservationPoliciesUpdateIn,
    ReservationSettingsOut,
    ReservationSettingsUpdateIn,
    ReservationStatusHistoryOut,
    ReservationTableAssignmentOut,
    ReservationTimelineOut,
    ReservationTransitionIn,
    ReservationUpdateIn,
    RestaurantTableCreateIn,
    RestaurantTableOut,
    RestaurantTableUpdateIn,
    TableAssignIn,
    TableBlockCreateIn,
    TableBlockOut,
    TableMergeIn,
    TableSplitIn,
    TableStatusHistoryOut,
    TableStatusTransitionIn,
    WaitlistCreateIn,
    WaitlistOut,
    WaitlistPromoteIn,
    WalkInCreateIn,
)

router = APIRouter(prefix="/api/v1/reservations", tags=["reservations"])


async def _get_reservation_or_404(session: AsyncSession, reservation_id: uuid.UUID) -> Reservation:
    reservation = await service.get_reservation(session, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found.")
    return reservation


# --- Reservations ------------------------------------------------------------


@router.get("")
async def list_reservations(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
    reservation_status: str | None = Query(default=None),
    source: str | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    dining_area_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> PaginatedResponse[ReservationOut]:
    stmt = select(Reservation)
    count_stmt = select(func.count()).select_from(Reservation)

    if search:
        pattern = f"%{search}%"
        clause = or_(
            Reservation.reservation_number.ilike(pattern),
            Reservation.guest_name.ilike(pattern),
            Reservation.phone_e164.ilike(pattern),
        )
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if reservation_status:
        stmt = stmt.where(Reservation.status == reservation_status)
        count_stmt = count_stmt.where(Reservation.status == reservation_status)
    if source:
        stmt = stmt.where(Reservation.source == source)
        count_stmt = count_stmt.where(Reservation.source == source)
    if customer_id:
        stmt = stmt.where(Reservation.customer_id == customer_id)
        count_stmt = count_stmt.where(Reservation.customer_id == customer_id)
    if dining_area_id:
        stmt = stmt.where(Reservation.dining_area_id == dining_area_id)
        count_stmt = count_stmt.where(Reservation.dining_area_id == dining_area_id)
    if date_from:
        stmt = stmt.where(Reservation.reservation_date >= date_from)
        count_stmt = count_stmt.where(Reservation.reservation_date >= date_from)
    if date_to:
        stmt = stmt.where(Reservation.reservation_date <= date_to)
        count_stmt = count_stmt.where(Reservation.reservation_date <= date_to)

    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc())
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [ReservationOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/availability")
async def get_availability(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
    target_date: date = Query(...),
    start_time: time = Query(...),
    end_time: time | None = Query(default=None),
    party_size: int = Query(ge=1),
    dining_area_id: uuid.UUID | None = Query(default=None),
) -> DataResponse[list[RestaurantTableOut]]:
    available_tables = await availability.find_available_tables(
        session,
        target_date=target_date,
        start_time=start_time,
        end_time=end_time,
        party_size=party_size,
        dining_area_id=dining_area_id,
    )
    data = [RestaurantTableOut.model_validate(t) for t in available_tables]
    return DataResponse(data=data, meta=request_meta(request))


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
    target_date: date = Query(...),
) -> DataResponse[ReservationDashboardStatsOut]:
    stats = await dashboard.get_reservation_dashboard_stats(session, target_date=target_date)
    return DataResponse(data=stats, meta=request_meta(request))


@router.get("/customers/{customer_id}/stats")
async def get_customer_stats(
    request: Request,
    customer_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CustomerReservationStatsOut]:
    stats = await customer_stats.get_customer_reservation_stats(session, customer_id)
    return DataResponse(data=stats, meta=request_meta(request))


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_reservation(
    request: Request,
    payload: ReservationCreateIn,
    actor: StaffUser = Depends(require_permission("reservations.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationOut]:
    reservation = await service.create_reservation(
        session, actor=actor, payload=payload, request=request
    )
    return DataResponse(data=ReservationOut.model_validate(reservation), meta=request_meta(request))


@router.post("/walk-in", status_code=status.HTTP_201_CREATED)
async def create_walk_in(
    request: Request,
    payload: WalkInCreateIn,
    actor: StaffUser = Depends(require_permission("reservations.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationOut]:
    reservation = await walkin.create_walk_in(
        session, actor=actor, payload=payload, request=request
    )
    return DataResponse(data=ReservationOut.model_validate(reservation), meta=request_meta(request))


@router.get("/{reservation_id}")
async def get_reservation(
    request: Request,
    reservation_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationOut]:
    reservation = await _get_reservation_or_404(session, reservation_id)
    return DataResponse(data=ReservationOut.model_validate(reservation), meta=request_meta(request))


@router.patch("/{reservation_id}")
async def update_reservation(
    request: Request,
    reservation_id: uuid.UUID,
    payload: ReservationUpdateIn,
    actor: StaffUser = Depends(require_permission("reservations.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationOut]:
    reservation = await _get_reservation_or_404(session, reservation_id)
    reservation = await service.update_reservation(
        session, actor=actor, reservation=reservation, payload=payload, request=request
    )
    return DataResponse(data=ReservationOut.model_validate(reservation), meta=request_meta(request))


@router.post("/{reservation_id}/transition")
async def transition_reservation(
    request: Request,
    reservation_id: uuid.UUID,
    payload: ReservationTransitionIn,
    actor: StaffUser = Depends(require_permission("reservations.transition")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationOut]:
    reservation = await _get_reservation_or_404(session, reservation_id)
    await service.transition_reservation(
        session,
        actor=actor,
        reservation=reservation,
        new_status=payload.new_status,
        reason=payload.reason,
        request=request,
    )
    # Phase 13: schedules a review-request outreach after a completed visit
    # — see app.feedback.integrations's module docstring.
    await feedback_integrations.schedule_reservation_review_request(
        session, actor=actor, reservation=reservation, new_status=payload.new_status
    )
    return DataResponse(data=ReservationOut.model_validate(reservation), meta=request_meta(request))


@router.post("/{reservation_id}/approval")
async def decide_reservation_approval(
    request: Request,
    reservation_id: uuid.UUID,
    payload: ReservationApprovalIn,
    actor: StaffUser = Depends(require_permission("reservations.approve")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationOut]:
    reservation = await _get_reservation_or_404(session, reservation_id)
    if payload.approve:
        await service.approve_reservation(
            session, actor=actor, reservation=reservation, request=request
        )
    else:
        if not payload.reason:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="A rejection reason is required."
            )
        await service.reject_reservation(
            session, actor=actor, reservation=reservation, reason=payload.reason, request=request
        )
    return DataResponse(data=ReservationOut.model_validate(reservation), meta=request_meta(request))


@router.post("/{reservation_id}/assign-tables")
async def assign_reservation_tables(
    request: Request,
    reservation_id: uuid.UUID,
    payload: TableAssignIn,
    actor: StaffUser = Depends(require_permission("reservations.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ReservationTableAssignmentOut]]:
    reservation = await _get_reservation_or_404(session, reservation_id)
    assignments = await assignment.assign_tables(
        session,
        actor=actor,
        reservation=reservation,
        table_ids=payload.table_ids,
        request=request,
    )
    data = [ReservationTableAssignmentOut.model_validate(a) for a in assignments]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/{reservation_id}/unassign-tables")
async def unassign_reservation_tables(
    request: Request,
    reservation_id: uuid.UUID,
    release_tables: bool = Query(default=True),
    actor: StaffUser = Depends(require_permission("reservations.assign")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    reservation = await _get_reservation_or_404(session, reservation_id)
    await assignment.unassign_tables(
        session,
        actor=actor,
        reservation=reservation,
        release_tables=release_tables,
        request=request,
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/{reservation_id}/link-order")
async def link_reservation_order(
    request: Request,
    reservation_id: uuid.UUID,
    payload: ReservationOrderLinkIn,
    actor: StaffUser = Depends(require_permission("reservations.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationOut]:
    reservation = await _get_reservation_or_404(session, reservation_id)
    reservation = await order_link.link_order(
        session, actor=actor, reservation=reservation, order_id=payload.order_id, request=request
    )
    return DataResponse(data=ReservationOut.model_validate(reservation), meta=request_meta(request))


@router.get("/{reservation_id}/timeline")
async def get_reservation_timeline(
    request: Request,
    reservation_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
) -> PaginatedResponse[ReservationTimelineOut]:
    await _get_reservation_or_404(session, reservation_id)
    stmt = (
        select(ReservationTimeline)
        .where(ReservationTimeline.reservation_id == reservation_id)
        .order_by(ReservationTimeline.occurred_at.desc())
    )
    count_stmt = (
        select(func.count())
        .select_from(ReservationTimeline)
        .where(ReservationTimeline.reservation_id == reservation_id)
    )
    total = await session.scalar(count_stmt) or 0
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [ReservationTimelineOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.get("/{reservation_id}/status-history")
async def get_reservation_status_history(
    request: Request,
    reservation_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ReservationStatusHistoryOut]]:
    await _get_reservation_or_404(session, reservation_id)
    rows = (
        await session.scalars(
            select(ReservationStatusHistory)
            .where(ReservationStatusHistory.reservation_id == reservation_id)
            .order_by(ReservationStatusHistory.created_at.desc())
        )
    ).all()
    data = [ReservationStatusHistoryOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.get("/{reservation_id}/notes")
async def list_reservation_notes(
    request: Request,
    reservation_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ReservationNoteOut]]:
    await _get_reservation_or_404(session, reservation_id)
    rows = (
        await session.scalars(
            select(ReservationNote)
            .where(
                ReservationNote.reservation_id == reservation_id,
                ReservationNote.deleted_at.is_(None),
            )
            .order_by(ReservationNote.created_at.desc())
        )
    ).all()
    data = [ReservationNoteOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/{reservation_id}/notes", status_code=status.HTTP_201_CREATED)
async def add_reservation_note(
    request: Request,
    reservation_id: uuid.UUID,
    payload: ReservationNoteIn,
    actor: StaffUser = Depends(require_permission("reservations.notes.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationNoteOut]:
    reservation = await _get_reservation_or_404(session, reservation_id)
    note = await service.add_note(
        session, actor=actor, reservation=reservation, payload=payload, request=request
    )
    return DataResponse(data=ReservationNoteOut.model_validate(note), meta=request_meta(request))


# --- Waitlist ----------------------------------------------------------------


@router.get("/waitlist")
async def list_waitlist(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.waitlist.manage")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    waitlist_status: str | None = Query(default=None),
) -> PaginatedResponse[WaitlistOut]:
    stmt = select(ReservationWaitlist)
    count_stmt = select(func.count()).select_from(ReservationWaitlist)
    if waitlist_status:
        stmt = stmt.where(ReservationWaitlist.status == waitlist_status)
        count_stmt = count_stmt.where(ReservationWaitlist.status == waitlist_status)

    total = await session.scalar(count_stmt) or 0
    stmt = stmt.order_by(
        ReservationWaitlist.priority.desc(), ReservationWaitlist.requested_at.asc()
    )
    stmt = stmt.offset((page_params.page - 1) * page_params.page_size).limit(page_params.page_size)
    rows = (await session.scalars(stmt)).all()
    data = [WaitlistOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


async def _get_waitlist_entry_or_404(
    session: AsyncSession, entry_id: uuid.UUID
) -> ReservationWaitlist:
    entry = await waitlist_service.get_waitlist_entry(session, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Waitlist entry not found."
        )
    return entry


@router.post("/waitlist", status_code=status.HTTP_201_CREATED)
async def add_to_waitlist(
    request: Request,
    payload: WaitlistCreateIn,
    actor: StaffUser = Depends(require_permission("reservations.waitlist.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[WaitlistOut]:
    entry = await waitlist_service.add_to_waitlist(
        session, actor=actor, payload=payload, request=request
    )
    return DataResponse(data=WaitlistOut.model_validate(entry), meta=request_meta(request))


@router.post("/waitlist/{entry_id}/notify")
async def notify_waitlist(
    request: Request,
    entry_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("reservations.waitlist.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[WaitlistOut]:
    entry = await _get_waitlist_entry_or_404(session, entry_id)
    await waitlist_service.notify_waitlist_entry(session, actor=actor, entry=entry, request=request)
    return DataResponse(data=WaitlistOut.model_validate(entry), meta=request_meta(request))


@router.post("/waitlist/{entry_id}/promote")
async def promote_waitlist(
    request: Request,
    entry_id: uuid.UUID,
    payload: WaitlistPromoteIn,
    actor: StaffUser = Depends(require_permission("reservations.waitlist.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[WaitlistOut]:
    entry = await _get_waitlist_entry_or_404(session, entry_id)
    reservation = await _get_reservation_or_404(session, payload.reservation_id)
    await waitlist_service.promote_waitlist_entry(
        session, actor=actor, entry=entry, reservation=reservation, request=request
    )
    return DataResponse(data=WaitlistOut.model_validate(entry), meta=request_meta(request))


@router.post("/waitlist/{entry_id}/cancel")
async def cancel_waitlist(
    request: Request,
    entry_id: uuid.UUID,
    payload: ArchiveIn,
    actor: StaffUser = Depends(require_permission("reservations.waitlist.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[WaitlistOut]:
    entry = await _get_waitlist_entry_or_404(session, entry_id)
    await waitlist_service.cancel_waitlist_entry(
        session, actor=actor, entry=entry, reason=payload.reason, request=request
    )
    return DataResponse(data=WaitlistOut.model_validate(entry), meta=request_meta(request))


# --- Dining areas -------------------------------------------------------


@router.get("/dining-areas")
async def list_dining_areas(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
    include_archived: bool = Query(default=False),
) -> DataResponse[list[DiningAreaOut]]:
    stmt = select(DiningArea).order_by(DiningArea.sort_order.asc())
    if not include_archived:
        stmt = stmt.where(DiningArea.deleted_at.is_(None))
    rows = (await session.scalars(stmt)).all()
    data = [DiningAreaOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/dining-areas", status_code=status.HTTP_201_CREATED)
async def create_dining_area(
    request: Request,
    payload: DiningAreaCreateIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DiningAreaOut]:
    dining_area = await tables.create_dining_area(
        session, actor=actor, payload=payload, request=request
    )
    return DataResponse(data=DiningAreaOut.model_validate(dining_area), meta=request_meta(request))


async def _get_dining_area_or_404(session: AsyncSession, dining_area_id: uuid.UUID) -> DiningArea:
    dining_area = await session.get(DiningArea, dining_area_id)
    if dining_area is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dining area not found.")
    return dining_area


@router.patch("/dining-areas/{dining_area_id}")
async def update_dining_area(
    request: Request,
    dining_area_id: uuid.UUID,
    payload: DiningAreaUpdateIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DiningAreaOut]:
    dining_area = await _get_dining_area_or_404(session, dining_area_id)
    dining_area = await tables.update_dining_area(
        session, actor=actor, dining_area=dining_area, payload=payload, request=request
    )
    return DataResponse(data=DiningAreaOut.model_validate(dining_area), meta=request_meta(request))


@router.delete("/dining-areas/{dining_area_id}")
async def archive_dining_area(
    request: Request,
    dining_area_id: uuid.UUID,
    payload: ArchiveIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    dining_area = await _get_dining_area_or_404(session, dining_area_id)
    await tables.archive_dining_area(
        session, actor=actor, dining_area=dining_area, reason=payload.reason, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/dining-areas/{dining_area_id}/restore")
async def restore_dining_area(
    request: Request,
    dining_area_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[DiningAreaOut]:
    dining_area = await _get_dining_area_or_404(session, dining_area_id)
    await tables.restore_dining_area(session, actor=actor, dining_area=dining_area, request=request)
    return DataResponse(data=DiningAreaOut.model_validate(dining_area), meta=request_meta(request))


# --- Tables --------------------------------------------------------------


@router.get("/tables")
async def list_tables(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
    dining_area_id: uuid.UUID | None = Query(default=None),
    table_status: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
) -> DataResponse[list[RestaurantTableOut]]:
    stmt = select(RestaurantTable).order_by(RestaurantTable.sort_order.asc())
    if not include_archived:
        stmt = stmt.where(RestaurantTable.deleted_at.is_(None))
    if dining_area_id:
        stmt = stmt.where(RestaurantTable.dining_area_id == dining_area_id)
    if table_status:
        stmt = stmt.where(RestaurantTable.status == table_status)
    rows = (await session.scalars(stmt)).all()
    data = [RestaurantTableOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/tables", status_code=status.HTTP_201_CREATED)
async def create_table(
    request: Request,
    payload: RestaurantTableCreateIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RestaurantTableOut]:
    table = await tables.create_table(session, actor=actor, payload=payload, request=request)
    return DataResponse(data=RestaurantTableOut.model_validate(table), meta=request_meta(request))


async def _get_table_or_404(session: AsyncSession, table_id: uuid.UUID) -> RestaurantTable:
    table = await tables.get_table(session, table_id)
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found.")
    return table


@router.get("/tables/{table_id}")
async def get_table(
    request: Request,
    table_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RestaurantTableOut]:
    table = await _get_table_or_404(session, table_id)
    return DataResponse(data=RestaurantTableOut.model_validate(table), meta=request_meta(request))


@router.patch("/tables/{table_id}")
async def update_table(
    request: Request,
    table_id: uuid.UUID,
    payload: RestaurantTableUpdateIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RestaurantTableOut]:
    table = await _get_table_or_404(session, table_id)
    table = await tables.update_table(
        session, actor=actor, table=table, payload=payload, request=request
    )
    return DataResponse(data=RestaurantTableOut.model_validate(table), meta=request_meta(request))


@router.delete("/tables/{table_id}")
async def archive_table(
    request: Request,
    table_id: uuid.UUID,
    payload: ArchiveIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    table = await _get_table_or_404(session, table_id)
    await tables.archive_table(
        session, actor=actor, table=table, reason=payload.reason, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/tables/{table_id}/restore")
async def restore_table(
    request: Request,
    table_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RestaurantTableOut]:
    table = await _get_table_or_404(session, table_id)
    await tables.restore_table(session, actor=actor, table=table, request=request)
    return DataResponse(data=RestaurantTableOut.model_validate(table), meta=request_meta(request))


@router.post("/tables/{table_id}/status")
async def transition_table_status(
    request: Request,
    table_id: uuid.UUID,
    payload: TableStatusTransitionIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RestaurantTableOut]:
    table = await _get_table_or_404(session, table_id)
    await tables.transition_table_status(
        session,
        actor=actor,
        table=table,
        new_status=payload.new_status,
        reason=payload.reason,
        request=request,
    )
    return DataResponse(data=RestaurantTableOut.model_validate(table), meta=request_meta(request))


@router.post("/tables/{table_id}/merge")
async def merge_tables(
    request: Request,
    table_id: uuid.UUID,
    payload: TableMergeIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[RestaurantTableOut]]:
    primary_table = await _get_table_or_404(session, table_id)
    secondary_tables = await tables.merge_tables(
        session,
        actor=actor,
        primary_table=primary_table,
        secondary_table_ids=payload.secondary_table_ids,
        reason=payload.reason,
        request=request,
    )
    data = [RestaurantTableOut.model_validate(t) for t in secondary_tables]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/tables/{table_id}/split")
async def split_tables(
    request: Request,
    table_id: uuid.UUID,
    payload: TableSplitIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[RestaurantTableOut]]:
    primary_table = await _get_table_or_404(session, table_id)
    released_tables = await tables.split_tables(
        session, actor=actor, primary_table=primary_table, reason=payload.reason, request=request
    )
    data = [RestaurantTableOut.model_validate(t) for t in released_tables]
    return DataResponse(data=data, meta=request_meta(request))


@router.get("/tables/{table_id}/status-history")
async def get_table_status_history(
    request: Request,
    table_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[TableStatusHistoryOut]]:
    await _get_table_or_404(session, table_id)
    rows = (
        await session.scalars(
            select(TableStatusHistory)
            .where(TableStatusHistory.restaurant_table_id == table_id)
            .order_by(TableStatusHistory.created_at.desc())
        )
    ).all()
    data = [TableStatusHistoryOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/tables/{table_id}/blocks", status_code=status.HTTP_201_CREATED)
async def create_table_block(
    request: Request,
    table_id: uuid.UUID,
    payload: TableBlockCreateIn,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TableBlockOut]:
    table = await _get_table_or_404(session, table_id)
    block = await tables.create_table_block(
        session, actor=actor, table=table, payload=payload, request=request
    )
    return DataResponse(data=TableBlockOut.model_validate(block), meta=request_meta(request))


@router.get("/tables/{table_id}/blocks")
async def list_table_blocks(
    request: Request,
    table_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
    active_only: bool = Query(default=True),
) -> DataResponse[list[TableBlockOut]]:
    await _get_table_or_404(session, table_id)
    stmt = select(TableBlock).where(TableBlock.restaurant_table_id == table_id)
    if active_only:
        stmt = stmt.where(TableBlock.is_active.is_(True))
    stmt = stmt.order_by(TableBlock.starts_at.desc())
    rows = (await session.scalars(stmt)).all()
    data = [TableBlockOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/tables/{table_id}/blocks/{block_id}/release")
async def release_table_block(
    request: Request,
    table_id: uuid.UUID,
    block_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("reservations.tables.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TableBlockOut]:
    table = await _get_table_or_404(session, table_id)
    block = await session.get(TableBlock, block_id)
    if block is None or block.restaurant_table_id != table_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found.")
    await tables.release_table_block(
        session, actor=actor, block=block, table=table, request=request
    )
    return DataResponse(data=TableBlockOut.model_validate(block), meta=request_meta(request))


# --- Business hours, holidays, policies, settings ----------------------------


@router.get("/business-hours")
async def list_business_hours(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[BusinessHoursOut]]:
    rows = (
        await session.scalars(select(BusinessHours).order_by(BusinessHours.day_of_week.asc()))
    ).all()
    data = [BusinessHoursOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.patch("/business-hours/{day_of_week}")
async def update_business_hours(
    request: Request,
    day_of_week: int,
    payload: BusinessHoursUpdateIn,
    actor: StaffUser = Depends(require_permission("reservations.settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[BusinessHoursOut]:
    business_hours = await session.scalar(
        select(BusinessHours).where(BusinessHours.day_of_week == day_of_week)
    )
    if business_hours is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Business hours not found."
        )
    business_hours = await settings_service.update_business_hours(
        session, actor=actor, business_hours=business_hours, payload=payload, request=request
    )
    return DataResponse(
        data=BusinessHoursOut.model_validate(business_hours), meta=request_meta(request)
    )


@router.get("/holidays")
async def list_holidays(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> DataResponse[list[HolidayCalendarOut]]:
    stmt = select(HolidayCalendar).where(HolidayCalendar.deleted_at.is_(None))
    if date_from:
        stmt = stmt.where(HolidayCalendar.holiday_date >= date_from)
    if date_to:
        stmt = stmt.where(HolidayCalendar.holiday_date <= date_to)
    stmt = stmt.order_by(HolidayCalendar.holiday_date.asc())
    rows = (await session.scalars(stmt)).all()
    data = [HolidayCalendarOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/holidays", status_code=status.HTTP_201_CREATED)
async def create_holiday(
    request: Request,
    payload: HolidayCalendarCreateIn,
    actor: StaffUser = Depends(require_permission("reservations.settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[HolidayCalendarOut]:
    holiday = await settings_service.create_holiday(
        session, actor=actor, payload=payload, request=request
    )
    return DataResponse(data=HolidayCalendarOut.model_validate(holiday), meta=request_meta(request))


async def _get_holiday_or_404(session: AsyncSession, holiday_id: uuid.UUID) -> HolidayCalendar:
    holiday = await session.get(HolidayCalendar, holiday_id)
    if holiday is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Holiday not found.")
    return holiday


@router.patch("/holidays/{holiday_id}")
async def update_holiday(
    request: Request,
    holiday_id: uuid.UUID,
    payload: HolidayCalendarUpdateIn,
    actor: StaffUser = Depends(require_permission("reservations.settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[HolidayCalendarOut]:
    holiday = await _get_holiday_or_404(session, holiday_id)
    holiday = await settings_service.update_holiday(
        session, actor=actor, holiday=holiday, payload=payload, request=request
    )
    return DataResponse(data=HolidayCalendarOut.model_validate(holiday), meta=request_meta(request))


@router.delete("/holidays/{holiday_id}")
async def archive_holiday(
    request: Request,
    holiday_id: uuid.UUID,
    payload: ArchiveIn,
    actor: StaffUser = Depends(require_permission("reservations.settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    holiday = await _get_holiday_or_404(session, holiday_id)
    await settings_service.archive_holiday(
        session, actor=actor, holiday=holiday, reason=payload.reason, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/holidays/{holiday_id}/restore")
async def restore_holiday(
    request: Request,
    holiday_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("reservations.settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[HolidayCalendarOut]:
    holiday = await _get_holiday_or_404(session, holiday_id)
    await settings_service.restore_holiday(session, actor=actor, holiday=holiday, request=request)
    return DataResponse(data=HolidayCalendarOut.model_validate(holiday), meta=request_meta(request))


@router.get("/policies")
async def get_policies(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationPoliciesOut]:
    policies = await session.scalar(select(ReservationPolicies).limit(1))
    if policies is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation policies have not been seeded.",
        )
    return DataResponse(
        data=ReservationPoliciesOut.model_validate(policies), meta=request_meta(request)
    )


@router.patch("/policies")
async def update_policies(
    request: Request,
    payload: ReservationPoliciesUpdateIn,
    actor: StaffUser = Depends(require_permission("reservations.settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationPoliciesOut]:
    policies = await session.scalar(select(ReservationPolicies).limit(1))
    if policies is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation policies have not been seeded.",
        )
    policies = await settings_service.update_reservation_policies(
        session, actor=actor, policies=policies, payload=payload, request=request
    )
    return DataResponse(
        data=ReservationPoliciesOut.model_validate(policies), meta=request_meta(request)
    )


@router.get("/settings")
async def get_settings(
    request: Request,
    _actor: StaffUser = Depends(require_permission("reservations.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationSettingsOut]:
    reservation_settings = await session.scalar(select(ReservationSettings).limit(1))
    if reservation_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation settings have not been seeded.",
        )
    return DataResponse(
        data=ReservationSettingsOut.model_validate(reservation_settings), meta=request_meta(request)
    )


@router.patch("/settings")
async def update_settings(
    request: Request,
    payload: ReservationSettingsUpdateIn,
    actor: StaffUser = Depends(require_permission("reservations.settings.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReservationSettingsOut]:
    reservation_settings = await session.scalar(select(ReservationSettings).limit(1))
    if reservation_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation settings have not been seeded.",
        )
    reservation_settings = await settings_service.update_reservation_settings(
        session, actor=actor, settings=reservation_settings, payload=payload, request=request
    )
    return DataResponse(
        data=ReservationSettingsOut.model_validate(reservation_settings), meta=request_meta(request)
    )
