"""Dining area, table, and floor-management business logic — kept out of
the router for the same reason as app.menu.service's category functions
(this module mirrors that exact create/update/archive/restore shape for
`DiningArea`, a managed reference table structurally identical to
`MenuCategory`).
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.db.models import DiningArea, RestaurantTable, StaffUser, TableBlock, TableStatusHistory
from app.db.models.restaurant_table import TABLE_STATUSES
from app.reservations.schemas import (
    DiningAreaCreateIn,
    DiningAreaUpdateIn,
    RestaurantTableCreateIn,
    RestaurantTableUpdateIn,
    TableBlockCreateIn,
)

# "Merged" is deliberately unreachable here — only `merge_tables` may set it,
# and only `split_tables` may clear it, the same "not through the generic
# transition path" treatment app.leads.states gives `won`. A table already
# `merged` must be split before any other status change applies to it.
ALLOWED_TABLE_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "available": frozenset({"reserved", "occupied", "cleaning", "blocked", "maintenance"}),
    "reserved": frozenset({"occupied", "available", "blocked"}),
    "occupied": frozenset({"cleaning", "available", "blocked"}),
    "cleaning": frozenset({"available", "blocked", "maintenance"}),
    "blocked": frozenset({"available", "maintenance"}),
    "maintenance": frozenset({"available"}),
    "merged": frozenset(),
}

assert set(ALLOWED_TABLE_STATUS_TRANSITIONS) == set(TABLE_STATUSES)

# A block's `block_type` maps to the table status it puts the table into
# while active, and every block type resolves back to `available` on
# release (a released table always re-enters circulation for review, never
# assumed straight back into `occupied`/`reserved`).
_BLOCK_TYPE_STATUS: dict[str, str] = {
    "cleaning": "cleaning",
    "maintenance": "maintenance",
    "private_event": "blocked",
    "other": "blocked",
}


def is_table_transition_allowed(current: str, target: str) -> bool:
    return target in ALLOWED_TABLE_STATUS_TRANSITIONS.get(current, frozenset())


# --- Dining areas -----------------------------------------------------------


async def create_dining_area(
    session: AsyncSession, *, actor: StaffUser, payload: DiningAreaCreateIn, request: Request | None
) -> DiningArea:
    existing = await session.scalar(select(DiningArea).where(DiningArea.code == payload.code))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A dining area with this code already exists.",
        )

    dining_area = DiningArea(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        created_by=actor.id,
    )
    session.add(dining_area)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="dining_area.created",
        target_type="dining_area",
        target_id=dining_area.id,
        request=request,
        safe_metadata={"code": dining_area.code},
    )
    return dining_area


async def update_dining_area(
    session: AsyncSession,
    *,
    actor: StaffUser,
    dining_area: DiningArea,
    payload: DiningAreaUpdateIn,
    request: Request | None,
) -> DiningArea:
    if payload.expected_version is not None and payload.expected_version != dining_area.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dining area was updated by someone else. Reload and try again.",
        )

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = {field: getattr(dining_area, field) for field in updates}
    for field, value in updates.items():
        setattr(dining_area, field, value)

    if updates:
        dining_area.version += 1
        dining_area.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="dining_area.updated",
            target_type="dining_area",
            target_id=dining_area.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return dining_area


async def archive_dining_area(
    session: AsyncSession,
    *,
    actor: StaffUser,
    dining_area: DiningArea,
    reason: str,
    request: Request | None,
) -> None:
    dining_area.deleted_at = datetime.now(UTC)
    dining_area.deleted_by = actor.id
    dining_area.deletion_reason = reason
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="dining_area.archived",
        target_type="dining_area",
        target_id=dining_area.id,
        request=request,
        safe_metadata={"reason": reason},
    )


async def restore_dining_area(
    session: AsyncSession, *, actor: StaffUser, dining_area: DiningArea, request: Request | None
) -> None:
    dining_area.deleted_at = None
    dining_area.deleted_by = None
    dining_area.deletion_reason = None
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="dining_area.restored",
        target_type="dining_area",
        target_id=dining_area.id,
        request=request,
    )


# --- Restaurant tables ------------------------------------------------------


async def get_table(session: AsyncSession, table_id: uuid.UUID) -> RestaurantTable | None:
    return await session.get(RestaurantTable, table_id)


async def create_table(
    session: AsyncSession,
    *,
    actor: StaffUser,
    payload: RestaurantTableCreateIn,
    request: Request | None,
) -> RestaurantTable:
    dining_area = await session.get(DiningArea, payload.dining_area_id)
    if dining_area is None or dining_area.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dining area not found.")

    existing = await session.scalar(
        select(RestaurantTable).where(
            RestaurantTable.table_number == payload.table_number,
            RestaurantTable.deleted_at.is_(None),
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A table with this number already exists.",
        )

    table = RestaurantTable(
        id=uuid.uuid4(),
        dining_area_id=payload.dining_area_id,
        table_number=payload.table_number,
        capacity=payload.capacity,
        minimum_capacity=payload.minimum_capacity or 1,
        maximum_capacity=payload.maximum_capacity,
        shape=payload.shape,
        status="available",
        is_wheelchair_accessible=payload.is_wheelchair_accessible,
        is_temporary=payload.is_temporary,
        qr_identifier=payload.qr_identifier,
        notes=payload.notes,
        sort_order=payload.sort_order,
        created_by=actor.id,
    )
    session.add(table)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="restaurant_table.created",
        target_type="restaurant_table",
        target_id=table.id,
        request=request,
        safe_metadata={"table_number": table.table_number},
    )
    return table


async def update_table(
    session: AsyncSession,
    *,
    actor: StaffUser,
    table: RestaurantTable,
    payload: RestaurantTableUpdateIn,
    request: Request | None,
) -> RestaurantTable:
    if payload.expected_version is not None and payload.expected_version != table.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This table was updated by someone else. Reload and try again.",
        )
    if payload.dining_area_id is not None:
        dining_area = await session.get(DiningArea, payload.dining_area_id)
        if dining_area is None or dining_area.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Dining area not found."
            )

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = {field: getattr(table, field) for field in updates}
    for field, value in updates.items():
        setattr(table, field, value)

    if updates:
        table.version += 1
        table.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="restaurant_table.updated",
            target_type="restaurant_table",
            target_id=table.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return table


async def archive_table(
    session: AsyncSession,
    *,
    actor: StaffUser,
    table: RestaurantTable,
    reason: str,
    request: Request | None,
) -> None:
    table.deleted_at = datetime.now(UTC)
    table.deleted_by = actor.id
    table.deletion_reason = reason
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="restaurant_table.archived",
        target_type="restaurant_table",
        target_id=table.id,
        request=request,
        safe_metadata={"reason": reason},
    )


async def restore_table(
    session: AsyncSession, *, actor: StaffUser, table: RestaurantTable, request: Request | None
) -> None:
    table.deleted_at = None
    table.deleted_by = None
    table.deletion_reason = None
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="restaurant_table.restored",
        target_type="restaurant_table",
        target_id=table.id,
        request=request,
    )


async def _record_table_status_change(
    session: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    table: RestaurantTable,
    new_status: str,
    reason: str | None,
    event_metadata: dict[str, Any] | None = None,
) -> None:
    previous_status = table.status
    table.status = new_status
    table.version += 1
    table.updated_by = actor_id
    session.add(
        TableStatusHistory(
            id=uuid.uuid4(),
            restaurant_table_id=table.id,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason,
            event_metadata=event_metadata,
            changed_by=actor_id,
        )
    )


async def transition_table_status(
    session: AsyncSession,
    *,
    actor: StaffUser,
    table: RestaurantTable,
    new_status: str,
    reason: str | None,
    request: Request | None,
) -> None:
    if table.status == "merged":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This table is merged; split it before changing its status.",
        )
    if not is_table_transition_allowed(table.status, new_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot move a table from '{table.status}' to '{new_status}'.",
        )

    previous_status = table.status
    await _record_table_status_change(
        session, actor_id=actor.id, table=table, new_status=new_status, reason=reason
    )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="restaurant_table.status_changed",
        target_type="restaurant_table",
        target_id=table.id,
        request=request,
        before_summary={"status": previous_status},
        after_summary={"status": new_status},
        safe_metadata={"reason": reason},
    )


async def merge_tables(
    session: AsyncSession,
    *,
    actor: StaffUser,
    primary_table: RestaurantTable,
    secondary_table_ids: list[uuid.UUID],
    reason: str | None,
    request: Request | None,
) -> list[RestaurantTable]:
    if primary_table.status == "merged":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The primary table is itself merged into another group.",
        )
    if primary_table.id in secondary_table_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A table cannot be merged with itself.",
        )

    secondary_tables = []
    for secondary_id in secondary_table_ids:
        secondary = await session.get(RestaurantTable, secondary_id)
        if secondary is None or secondary.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Table {secondary_id} not found.",
            )
        if secondary.status == "merged":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table {secondary.table_number} is already merged into another group.",
            )
        secondary_tables.append(secondary)

    for secondary in secondary_tables:
        secondary.merged_with_table_id = primary_table.id
        await _record_table_status_change(
            session,
            actor_id=actor.id,
            table=secondary,
            new_status="merged",
            reason=reason,
            event_metadata={"merged_with_table_id": str(primary_table.id)},
        )

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="restaurant_table.merged",
        target_type="restaurant_table",
        target_id=primary_table.id,
        request=request,
        safe_metadata={
            "secondary_table_ids": [str(t.id) for t in secondary_tables],
            "reason": reason,
        },
    )
    return secondary_tables


async def split_tables(
    session: AsyncSession,
    *,
    actor: StaffUser,
    primary_table: RestaurantTable,
    reason: str | None,
    request: Request | None,
) -> list[RestaurantTable]:
    merged_tables = (
        await session.scalars(
            select(RestaurantTable).where(RestaurantTable.merged_with_table_id == primary_table.id)
        )
    ).all()
    if not merged_tables:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This table has no merged tables to split.",
        )

    for table in merged_tables:
        table.merged_with_table_id = None
        await _record_table_status_change(
            session,
            actor_id=actor.id,
            table=table,
            new_status="available",
            reason=reason,
            event_metadata={"split_from_table_id": str(primary_table.id)},
        )

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="restaurant_table.split",
        target_type="restaurant_table",
        target_id=primary_table.id,
        request=request,
        safe_metadata={
            "secondary_table_ids": [str(t.id) for t in merged_tables],
            "reason": reason,
        },
    )
    return list(merged_tables)


# --- Table blocks ------------------------------------------------------------


async def create_table_block(
    session: AsyncSession,
    *,
    actor: StaffUser,
    table: RestaurantTable,
    payload: TableBlockCreateIn,
    request: Request | None,
) -> TableBlock:
    if table.status == "merged":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This table is merged; split it before blocking it.",
        )
    new_status = _BLOCK_TYPE_STATUS[payload.block_type]
    if not is_table_transition_allowed(table.status, new_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot block a table currently '{table.status}'.",
        )

    block = TableBlock(
        id=uuid.uuid4(),
        restaurant_table_id=table.id,
        block_type=payload.block_type,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        reason=payload.reason,
        is_active=True,
        created_by=actor.id,
    )
    session.add(block)
    await _record_table_status_change(
        session,
        actor_id=actor.id,
        table=table,
        new_status=new_status,
        reason=payload.reason,
        event_metadata={"block_type": payload.block_type},
    )
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="table_block.created",
        target_type="table_block",
        target_id=block.id,
        request=request,
        safe_metadata={"table_id": str(table.id), "block_type": payload.block_type},
    )
    return block


async def release_table_block(
    session: AsyncSession,
    *,
    actor: StaffUser,
    block: TableBlock,
    table: RestaurantTable,
    request: Request | None,
) -> None:
    if not block.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This block has already been released."
        )

    block.is_active = False
    block.released_by = actor.id
    block.released_at = datetime.now(UTC)
    block.updated_by = actor.id
    block.version += 1

    if table.status != "merged" and is_table_transition_allowed(table.status, "available"):
        await _record_table_status_change(
            session,
            actor_id=actor.id,
            table=table,
            new_status="available",
            reason="Block released.",
        )

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="table_block.released",
        target_type="table_block",
        target_id=block.id,
        request=request,
        safe_metadata={"table_id": str(table.id)},
    )
