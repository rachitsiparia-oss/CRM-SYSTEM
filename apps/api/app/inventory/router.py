import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import (
    InventoryBatch,
    InventoryCategory,
    InventoryItem,
    Recipe,
    RecipeItem,
    StaffUser,
    StockAdjustment,
    StockCount,
    StockCountLine,
    StockMovement,
    StockReceipt,
    StockReceiptItem,
    StockTransfer,
    StockTransferItem,
    StorageLocation,
    Supplier,
    UnitOfMeasure,
    WastageRecord,
)
from app.db.session import get_db
from app.inventory import (
    adjustments,
    balances,
    dashboard,
    receipts,
    stock_counts,
    transfers,
    wastage,
)
from app.inventory import items as item_service
from app.inventory import recipes as recipe_service
from app.inventory.schemas import (
    AdjustmentCreateIn,
    AdjustmentOut,
    BalanceDriftOut,
    BalanceRebuildResultOut,
    IngredientCostOut,
    InventoryCategoryCreateIn,
    InventoryCategoryOut,
    InventoryCategoryUpdateIn,
    InventoryDashboardStatsOut,
    InventoryItemCreateIn,
    InventoryItemListItemOut,
    InventoryItemOut,
    InventoryItemUpdateIn,
    ReceiptCreateIn,
    ReceiptItemCreateIn,
    ReceiptItemOut,
    ReceiptListItemOut,
    ReceiptOut,
    ReceiptReverseIn,
    RecipeCostOut,
    RecipeCreateIn,
    RecipeItemCreateIn,
    RecipeItemOut,
    RecipeListItemOut,
    RecipeOut,
    StockBalanceOut,
    StockCountCreateIn,
    StockCountLineOut,
    StockCountLineRecordIn,
    StockCountListItemOut,
    StockCountOut,
    StockMovementOut,
    StorageLocationCreateIn,
    StorageLocationOut,
    StorageLocationUpdateIn,
    SupplierCreateIn,
    SupplierOut,
    SupplierUpdateIn,
    TransferCreateIn,
    TransferItemCreateIn,
    TransferItemOut,
    TransferListItemOut,
    TransferOut,
    TransferReverseIn,
    UnitCreateIn,
    UnitOut,
    UnitUpdateIn,
    WastageCreateIn,
    WastageOut,
)
from app.permissions.dependencies import require_permission

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


def _apply_updates(entity: Any, payload: Any, *, actor_id: uuid.UUID) -> dict[str, Any]:
    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = {field: getattr(entity, field) for field in updates}
    for field, value in updates.items():
        setattr(entity, field, value)
    if updates:
        entity.version += 1
        entity.updated_by = actor_id
    return before


def _check_version(entity: Any, expected_version: int | None) -> None:
    if expected_version is not None and expected_version != entity.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This record was updated by someone else. Reload and try again.",
        )


# --- Units of measure ---------------------------------------------------------


@router.get("/units")
async def list_units(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    include_archived: bool = Query(default=False),
) -> DataResponse[list[UnitOut]]:
    stmt = select(UnitOfMeasure).order_by(UnitOfMeasure.unit_type, UnitOfMeasure.sort_order)
    if not include_archived:
        stmt = stmt.where(UnitOfMeasure.deleted_at.is_(None))
    rows = (await session.scalars(stmt)).all()
    return DataResponse(data=[UnitOut.model_validate(r) for r in rows], meta=request_meta(request))


@router.post("/units", status_code=status.HTTP_201_CREATED)
async def create_unit(
    request: Request,
    payload: UnitCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.units.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[UnitOut]:
    if payload.base_unit_id is not None:
        base = await session.get(UnitOfMeasure, payload.base_unit_id)
        if base is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Base unit not found."
            )
    unit = UnitOfMeasure(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        symbol=payload.symbol,
        unit_type=payload.unit_type,
        base_unit_id=payload.base_unit_id,
        conversion_factor=payload.conversion_factor,
        decimal_places=payload.decimal_places,
        sort_order=payload.sort_order,
        created_by=actor.id,
    )
    session.add(unit)
    await session.flush()
    return DataResponse(data=UnitOut.model_validate(unit), meta=request_meta(request))


@router.patch("/units/{unit_id}")
async def update_unit(
    request: Request,
    unit_id: uuid.UUID,
    payload: UnitUpdateIn,
    actor: StaffUser = Depends(require_permission("inventory.units.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[UnitOut]:
    unit = await session.get(UnitOfMeasure, unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found.")
    _check_version(unit, payload.expected_version)
    _apply_updates(unit, payload, actor_id=actor.id)
    await session.flush()
    return DataResponse(data=UnitOut.model_validate(unit), meta=request_meta(request))


# --- Categories -----------------------------------------------------------------


@router.get("/categories")
async def list_categories(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    include_archived: bool = Query(default=False),
) -> DataResponse[list[InventoryCategoryOut]]:
    stmt = select(InventoryCategory).order_by(InventoryCategory.sort_order)
    if not include_archived:
        stmt = stmt.where(InventoryCategory.deleted_at.is_(None))
    rows = (await session.scalars(stmt)).all()
    return DataResponse(
        data=[InventoryCategoryOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    request: Request,
    payload: InventoryCategoryCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[InventoryCategoryOut]:
    category = InventoryCategory(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        created_by=actor.id,
    )
    session.add(category)
    await session.flush()
    return DataResponse(
        data=InventoryCategoryOut.model_validate(category), meta=request_meta(request)
    )


@router.patch("/categories/{category_id}")
async def update_category(
    request: Request,
    category_id: uuid.UUID,
    payload: InventoryCategoryUpdateIn,
    actor: StaffUser = Depends(require_permission("inventory.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[InventoryCategoryOut]:
    category = await session.get(InventoryCategory, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    _check_version(category, payload.expected_version)
    _apply_updates(category, payload, actor_id=actor.id)
    await session.flush()
    return DataResponse(
        data=InventoryCategoryOut.model_validate(category), meta=request_meta(request)
    )


# --- Storage locations -----------------------------------------------------------


@router.get("/locations")
async def list_locations(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    include_archived: bool = Query(default=False),
) -> DataResponse[list[StorageLocationOut]]:
    stmt = select(StorageLocation).order_by(StorageLocation.sort_order)
    if not include_archived:
        stmt = stmt.where(StorageLocation.deleted_at.is_(None))
    rows = (await session.scalars(stmt)).all()
    return DataResponse(
        data=[StorageLocationOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.post("/locations", status_code=status.HTTP_201_CREATED)
async def create_location(
    request: Request,
    payload: StorageLocationCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.locations.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StorageLocationOut]:
    location = StorageLocation(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        location_type=payload.location_type,
        allows_negative_stock=payload.allows_negative_stock,
        sort_order=payload.sort_order,
        created_by=actor.id,
    )
    session.add(location)
    await session.flush()
    return DataResponse(
        data=StorageLocationOut.model_validate(location), meta=request_meta(request)
    )


@router.patch("/locations/{location_id}")
async def update_location(
    request: Request,
    location_id: uuid.UUID,
    payload: StorageLocationUpdateIn,
    actor: StaffUser = Depends(require_permission("inventory.locations.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StorageLocationOut]:
    location = await session.get(StorageLocation, location_id)
    if location is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found.")
    _check_version(location, payload.expected_version)
    _apply_updates(location, payload, actor_id=actor.id)
    await session.flush()
    return DataResponse(
        data=StorageLocationOut.model_validate(location), meta=request_meta(request)
    )


# --- Suppliers --------------------------------------------------------------------


@router.get("/suppliers")
async def list_suppliers(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
) -> PaginatedResponse[SupplierOut]:
    stmt = select(Supplier).where(Supplier.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(Supplier).where(Supplier.deleted_at.is_(None))
    if search:
        pattern = f"%{search}%"
        clause = or_(Supplier.name.ilike(pattern), Supplier.supplier_code.ilike(pattern))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(Supplier.name)
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[SupplierOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/suppliers", status_code=status.HTTP_201_CREATED)
async def create_supplier(
    request: Request,
    payload: SupplierCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.suppliers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SupplierOut]:
    supplier = Supplier(id=uuid.uuid4(), created_by=actor.id, **payload.model_dump())
    session.add(supplier)
    await session.flush()
    return DataResponse(data=SupplierOut.model_validate(supplier), meta=request_meta(request))


@router.get("/suppliers/{supplier_id}")
async def get_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SupplierOut]:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    return DataResponse(data=SupplierOut.model_validate(supplier), meta=request_meta(request))


@router.patch("/suppliers/{supplier_id}")
async def update_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    payload: SupplierUpdateIn,
    actor: StaffUser = Depends(require_permission("inventory.suppliers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SupplierOut]:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    _check_version(supplier, payload.expected_version)
    _apply_updates(supplier, payload, actor_id=actor.id)
    await session.flush()
    return DataResponse(data=SupplierOut.model_validate(supplier), meta=request_meta(request))


@router.delete("/suppliers/{supplier_id}")
async def archive_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.suppliers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    supplier.status = "archived"
    supplier.deleted_at = datetime.now(UTC)
    supplier.deleted_by = actor.id
    supplier.version += 1
    await session.flush()
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/suppliers/{supplier_id}/restore")
async def restore_supplier(
    request: Request,
    supplier_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.suppliers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[SupplierOut]:
    supplier = await session.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found.")
    supplier.status = "active"
    supplier.deleted_at = None
    supplier.deleted_by = None
    supplier.version += 1
    await session.flush()
    return DataResponse(data=SupplierOut.model_validate(supplier), meta=request_meta(request))


# --- Inventory items ---------------------------------------------------------------

_ITEM_SORT_MAP: dict[str, ColumnElement[Any]] = {
    "name": InventoryItem.name.asc(),
    "newest": InventoryItem.created_at.desc(),
    "oldest": InventoryItem.created_at.asc(),
    "available_quantity": (InventoryItem.current_stock - InventoryItem.reserved_stock).desc(),
    "stock_value": InventoryItem.current_stock.desc(),
}


async def _get_item_or_404(session: AsyncSession, item_id: uuid.UUID) -> InventoryItem:
    item = await session.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found."
        )
    return item


@router.get("/items")
async def list_items(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
    category_id: uuid.UUID | None = Query(default=None),
    location_id: uuid.UUID | None = Query(default=None),
    supplier_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    include_archived: bool = Query(default=False),
    low_stock: bool = Query(default=False),
    out_of_stock: bool = Query(default=False),
    perishable: bool | None = Query(default=None),
    batch_tracked: bool | None = Query(default=None),
    expiry_tracked: bool | None = Query(default=None),
    sort: str = Query(default="name"),
) -> PaginatedResponse[InventoryItemListItemOut]:
    if sort not in _ITEM_SORT_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort option."
        )

    stmt = select(InventoryItem)
    count_stmt = select(func.count()).select_from(InventoryItem)
    if not include_archived:
        stmt = stmt.where(InventoryItem.deleted_at.is_(None))
        count_stmt = count_stmt.where(InventoryItem.deleted_at.is_(None))

    if search:
        pattern = f"%{search}%"
        clause = or_(
            InventoryItem.name.ilike(pattern),
            InventoryItem.item_code.ilike(pattern),
            InventoryItem.barcode.ilike(pattern),
        )
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if category_id:
        stmt = stmt.where(InventoryItem.category_id == category_id)
        count_stmt = count_stmt.where(InventoryItem.category_id == category_id)
    if location_id:
        stmt = stmt.where(InventoryItem.default_location_id == location_id)
        count_stmt = count_stmt.where(InventoryItem.default_location_id == location_id)
    if supplier_id:
        clause = InventoryItem.preferred_supplier_id == supplier_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if is_active is not None:
        stmt = stmt.where(InventoryItem.is_active == is_active)
        count_stmt = count_stmt.where(InventoryItem.is_active == is_active)
    if low_stock:
        clause = InventoryItem.stock_status.in_(("low_stock", "critical_stock"))
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if out_of_stock:
        clause = InventoryItem.stock_status == "out_of_stock"
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if perishable is not None:
        stmt = stmt.where(InventoryItem.is_perishable == perishable)
        count_stmt = count_stmt.where(InventoryItem.is_perishable == perishable)
    if batch_tracked is not None:
        clause = InventoryItem.requires_batch_tracking == batch_tracked
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if expiry_tracked is not None:
        clause = InventoryItem.requires_expiry_tracking == expiry_tracked
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)

    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(_ITEM_SORT_MAP[sort])
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[InventoryItemListItemOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def create_item(
    request: Request,
    payload: InventoryItemCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.items.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[InventoryItemOut]:
    fields = payload.model_dump(exclude={"item_code"})
    item = InventoryItem(
        id=uuid.uuid4(),
        item_code=payload.item_code or item_service.generate_item_code(),
        created_by=actor.id,
        **fields,
    )
    session.add(item)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.item.created",
        target_type="inventory_item",
        target_id=item.id,
        request=request,
        safe_metadata={"item_code": item.item_code, "name": item.name},
    )
    return DataResponse(data=InventoryItemOut.model_validate(item), meta=request_meta(request))


@router.get("/items/{item_id}")
async def get_item(
    request: Request,
    item_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[InventoryItemOut]:
    item = await _get_item_or_404(session, item_id)
    return DataResponse(data=InventoryItemOut.model_validate(item), meta=request_meta(request))


@router.patch("/items/{item_id}")
async def update_item(
    request: Request,
    item_id: uuid.UUID,
    payload: InventoryItemUpdateIn,
    actor: StaffUser = Depends(require_permission("inventory.items.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[InventoryItemOut]:
    item = await _get_item_or_404(session, item_id)
    _check_version(item, payload.expected_version)
    before = _apply_updates(item, payload, actor_id=actor.id)
    await session.flush()
    if before:
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="inventory.item.updated",
            target_type="inventory_item",
            target_id=item.id,
            request=request,
            before_summary={k: str(v) for k, v in before.items()},
        )
    return DataResponse(data=InventoryItemOut.model_validate(item), meta=request_meta(request))


@router.delete("/items/{item_id}")
async def archive_item(
    request: Request,
    item_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.items.archive")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    item = await _get_item_or_404(session, item_id)
    item.is_active = False
    item.deleted_at = datetime.now(UTC)
    item.deleted_by = actor.id
    item.version += 1
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.item.archived",
        target_type="inventory_item",
        target_id=item.id,
        request=request,
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/items/{item_id}/restore")
async def restore_item(
    request: Request,
    item_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.items.restore")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[InventoryItemOut]:
    item = await _get_item_or_404(session, item_id)
    item.is_active = True
    item.deleted_at = None
    item.deleted_by = None
    item.version += 1
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.item.restored",
        target_type="inventory_item",
        target_id=item.id,
        request=request,
    )
    return DataResponse(data=InventoryItemOut.model_validate(item), meta=request_meta(request))


@router.get("/items/{item_id}/balances")
async def get_item_balances(
    request: Request,
    item_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[StockBalanceOut]]:
    await _get_item_or_404(session, item_id)
    from app.db.models import StockBalance

    rows = (
        await session.scalars(select(StockBalance).where(StockBalance.inventory_item_id == item_id))
    ).all()
    return DataResponse(
        data=[StockBalanceOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.get("/items/{item_id}/batches")
async def get_item_batches(
    request: Request,
    item_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    include_depleted: bool = Query(default=False),
) -> DataResponse[list[Any]]:
    from app.inventory.schemas import InventoryBatchOut

    await _get_item_or_404(session, item_id)
    stmt = select(InventoryBatch).where(InventoryBatch.inventory_item_id == item_id)
    if not include_depleted:
        stmt = stmt.where(InventoryBatch.status != "depleted")
    stmt = stmt.order_by(InventoryBatch.expires_at.is_(None), InventoryBatch.expires_at.asc())
    rows = (await session.scalars(stmt)).all()
    return DataResponse(
        data=[InventoryBatchOut.model_validate(r) for r in rows], meta=request_meta(request)
    )


@router.get("/items/{item_id}/movements")
async def get_item_movements(
    request: Request,
    item_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
) -> PaginatedResponse[StockMovementOut]:
    await _get_item_or_404(session, item_id)
    stmt = select(StockMovement).where(StockMovement.inventory_item_id == item_id)
    count_stmt = (
        select(func.count())
        .select_from(StockMovement)
        .where(StockMovement.inventory_item_id == item_id)
    )
    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(StockMovement.occurred_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[StockMovementOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


# --- Movement ledger (global) ------------------------------------------------------


@router.get("/movements")
async def list_movements(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    movement_type: str | None = Query(default=None),
    inventory_item_id: uuid.UUID | None = Query(default=None),
    storage_location_id: uuid.UUID | None = Query(default=None),
    reference_type: str | None = Query(default=None),
    reference_id: uuid.UUID | None = Query(default=None),
    performed_by: uuid.UUID | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
) -> PaginatedResponse[StockMovementOut]:
    stmt = select(StockMovement)
    count_stmt = select(func.count()).select_from(StockMovement)
    if movement_type:
        stmt, count_stmt = (
            stmt.where(StockMovement.movement_type == movement_type),
            count_stmt.where(StockMovement.movement_type == movement_type),
        )
    if inventory_item_id:
        clause = StockMovement.inventory_item_id == inventory_item_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if storage_location_id:
        clause = StockMovement.storage_location_id == storage_location_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if reference_type:
        clause = StockMovement.reference_type == reference_type
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if reference_id:
        clause = StockMovement.reference_id == reference_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if performed_by:
        clause = StockMovement.performed_by == performed_by
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if date_from:
        stmt, count_stmt = (
            stmt.where(StockMovement.occurred_at >= date_from),
            count_stmt.where(StockMovement.occurred_at >= date_from),
        )
    if date_to:
        stmt, count_stmt = (
            stmt.where(StockMovement.occurred_at <= date_to),
            count_stmt.where(StockMovement.occurred_at <= date_to),
        )

    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(StockMovement.occurred_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[StockMovementOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


# --- Balance verification and rebuild -----------------------------------------------


@router.get("/balances/verify")
async def verify_balances_endpoint(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    inventory_item_id: uuid.UUID | None = Query(default=None),
) -> DataResponse[list[BalanceDriftOut]]:
    drifts = await balances.verify_balances(session, inventory_item_id=inventory_item_id)
    data = [
        BalanceDriftOut(
            inventory_item_id=d.inventory_item_id,
            storage_location_id=d.storage_location_id,
            batch_id=d.batch_id,
            projected_on_hand=d.projected_on_hand,
            ledger_on_hand=d.ledger_on_hand,
            difference=d.difference,
        )
        for d in drifts
    ]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/balances/rebuild")
async def rebuild_balances_endpoint(
    request: Request,
    actor: StaffUser = Depends(require_permission("inventory.balances.rebuild")),
    session: AsyncSession = Depends(get_db),
    inventory_item_id: uuid.UUID | None = Query(default=None),
) -> DataResponse[BalanceRebuildResultOut]:
    summary = await balances.rebuild_balances(
        session, actor=actor, request=request, inventory_item_id=inventory_item_id
    )
    return DataResponse(data=BalanceRebuildResultOut(**summary), meta=request_meta(request))


# --- Receipts -----------------------------------------------------------------------


@router.get("/receipts")
async def list_receipts(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    status_filter: str | None = Query(default=None, alias="status"),
    supplier_id: uuid.UUID | None = Query(default=None),
) -> PaginatedResponse[ReceiptListItemOut]:
    stmt = select(StockReceipt)
    count_stmt = select(func.count()).select_from(StockReceipt)
    if status_filter:
        stmt, count_stmt = (
            stmt.where(StockReceipt.status == status_filter),
            count_stmt.where(StockReceipt.status == status_filter),
        )
    if supplier_id:
        clause = StockReceipt.supplier_id == supplier_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(StockReceipt.created_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[ReceiptListItemOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


async def _get_receipt_or_404(session: AsyncSession, receipt_id: uuid.UUID) -> StockReceipt:
    receipt = await session.get(StockReceipt, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found.")
    return receipt


async def _build_receipt_out(session: AsyncSession, receipt: StockReceipt) -> ReceiptOut:
    items = (
        await session.scalars(
            select(StockReceiptItem).where(StockReceiptItem.receipt_id == receipt.id)
        )
    ).all()
    return ReceiptOut.model_validate(receipt).model_copy(
        update={"items": [ReceiptItemOut.model_validate(i) for i in items]}
    )


@router.post("/receipts", status_code=status.HTTP_201_CREATED)
async def create_receipt(
    request: Request,
    payload: ReceiptCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.receipts.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReceiptOut]:
    receipt = await receipts.create_receipt(
        session,
        actor=actor,
        supplier_id=payload.supplier_id,
        storage_location_id=payload.storage_location_id,
        received_date=payload.received_date,
        supplier_reference=payload.supplier_reference,
        notes=payload.notes,
    )
    out = await _build_receipt_out(session, receipt)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/receipts/{receipt_id}")
async def get_receipt(
    request: Request,
    receipt_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReceiptOut]:
    receipt = await _get_receipt_or_404(session, receipt_id)
    out = await _build_receipt_out(session, receipt)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/receipts/{receipt_id}/items", status_code=status.HTTP_201_CREATED)
async def add_receipt_item(
    request: Request,
    receipt_id: uuid.UUID,
    payload: ReceiptItemCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.receipts.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReceiptItemOut]:
    receipt = await _get_receipt_or_404(session, receipt_id)
    item = await receipts.add_receipt_item(
        session,
        receipt=receipt,
        inventory_item_id=payload.inventory_item_id,
        purchase_unit_id=payload.purchase_unit_id,
        received_quantity=payload.received_quantity,
        accepted_quantity=payload.accepted_quantity,
        rejected_quantity=payload.rejected_quantity,
        unit_cost_minor=payload.unit_cost_minor,
        batch_code=payload.batch_code,
        manufactured_at=payload.manufactured_at,
        expires_at=payload.expires_at,
        notes=payload.notes,
    )
    return DataResponse(data=ReceiptItemOut.model_validate(item), meta=request_meta(request))


@router.post("/receipts/{receipt_id}/post")
async def post_receipt(
    request: Request,
    receipt_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.receipts.post")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReceiptOut]:
    receipt = await _get_receipt_or_404(session, receipt_id)
    receipt = await receipts.post_receipt(session, actor=actor, receipt=receipt, request=request)
    out = await _build_receipt_out(session, receipt)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/receipts/{receipt_id}/reverse")
async def reverse_receipt(
    request: Request,
    receipt_id: uuid.UUID,
    payload: ReceiptReverseIn,
    actor: StaffUser = Depends(require_permission("inventory.receipts.reverse")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ReceiptOut]:
    receipt = await _get_receipt_or_404(session, receipt_id)
    receipt = await receipts.reverse_receipt(
        session, actor=actor, receipt=receipt, reason=payload.reason, request=request
    )
    out = await _build_receipt_out(session, receipt)
    return DataResponse(data=out, meta=request_meta(request))


# --- Adjustments --------------------------------------------------------------------


@router.get("/adjustments")
async def list_adjustments(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    inventory_item_id: uuid.UUID | None = Query(default=None),
) -> PaginatedResponse[AdjustmentOut]:
    stmt = select(StockAdjustment)
    count_stmt = select(func.count()).select_from(StockAdjustment)
    if inventory_item_id:
        clause = StockAdjustment.inventory_item_id == inventory_item_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(StockAdjustment.created_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[AdjustmentOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/adjustments", status_code=status.HTTP_201_CREATED)
async def create_adjustment(
    request: Request,
    payload: AdjustmentCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.adjustments.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[AdjustmentOut]:
    approved_by = payload.approved_by
    if approved_by is not None:
        from app.permissions.service import has_permission

        if not await has_permission(session, approved_by, "inventory.adjustments.approve"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The named approver does not hold inventory.adjustments.approve.",
            )
    adjustment = await adjustments.create_adjustment(
        session,
        actor=actor,
        inventory_item_id=payload.inventory_item_id,
        storage_location_id=payload.storage_location_id,
        batch_id=payload.batch_id,
        direction=payload.direction,
        quantity=payload.quantity,
        reason_category=payload.reason_category,
        reason=payload.reason,
        approved_by=approved_by,
        idempotency_key=payload.idempotency_key,
        request=request,
    )
    return DataResponse(data=AdjustmentOut.model_validate(adjustment), meta=request_meta(request))


# --- Wastage -------------------------------------------------------------------------


@router.get("/wastage")
async def list_wastage(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    inventory_item_id: uuid.UUID | None = Query(default=None),
    reason_category: str | None = Query(default=None),
) -> PaginatedResponse[WastageOut]:
    stmt = select(WastageRecord)
    count_stmt = select(func.count()).select_from(WastageRecord)
    if inventory_item_id:
        clause = WastageRecord.inventory_item_id == inventory_item_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if reason_category:
        clause = WastageRecord.reason_category == reason_category
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(WastageRecord.created_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[WastageOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/wastage", status_code=status.HTTP_201_CREATED)
async def create_wastage(
    request: Request,
    payload: WastageCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.wastage.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[WastageOut]:
    record = await wastage.record_wastage(
        session,
        actor=actor,
        inventory_item_id=payload.inventory_item_id,
        storage_location_id=payload.storage_location_id,
        batch_id=payload.batch_id,
        quantity=payload.quantity,
        reason_category=payload.reason_category,
        reason=payload.reason,
        station=payload.station,
        related_order_id=payload.related_order_id,
        approved_by=payload.approved_by,
        idempotency_key=payload.idempotency_key,
        request=request,
    )
    return DataResponse(data=WastageOut.model_validate(record), meta=request_meta(request))


# --- Transfers -----------------------------------------------------------------------


@router.get("/transfers")
async def list_transfers(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    status_filter: str | None = Query(default=None, alias="status"),
) -> PaginatedResponse[TransferListItemOut]:
    stmt = select(StockTransfer)
    count_stmt = select(func.count()).select_from(StockTransfer)
    if status_filter:
        stmt, count_stmt = (
            stmt.where(StockTransfer.status == status_filter),
            count_stmt.where(StockTransfer.status == status_filter),
        )
    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(StockTransfer.created_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[TransferListItemOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


async def _get_transfer_or_404(session: AsyncSession, transfer_id: uuid.UUID) -> StockTransfer:
    transfer = await session.get(StockTransfer, transfer_id)
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found.")
    return transfer


async def _build_transfer_out(session: AsyncSession, transfer: StockTransfer) -> TransferOut:
    items = (
        await session.scalars(
            select(StockTransferItem).where(StockTransferItem.transfer_id == transfer.id)
        )
    ).all()
    return TransferOut.model_validate(transfer).model_copy(
        update={"items": [TransferItemOut.model_validate(i) for i in items]}
    )


@router.post("/transfers", status_code=status.HTTP_201_CREATED)
async def create_transfer(
    request: Request,
    payload: TransferCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.transfers.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TransferOut]:
    transfer = await transfers.create_transfer(
        session,
        actor=actor,
        source_location_id=payload.source_location_id,
        destination_location_id=payload.destination_location_id,
        notes=payload.notes,
    )
    out = await _build_transfer_out(session, transfer)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/transfers/{transfer_id}")
async def get_transfer(
    request: Request,
    transfer_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TransferOut]:
    transfer = await _get_transfer_or_404(session, transfer_id)
    out = await _build_transfer_out(session, transfer)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/transfers/{transfer_id}/items", status_code=status.HTTP_201_CREATED)
async def add_transfer_item(
    request: Request,
    transfer_id: uuid.UUID,
    payload: TransferItemCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.transfers.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TransferItemOut]:
    transfer = await _get_transfer_or_404(session, transfer_id)
    item = await transfers.add_transfer_item(
        session,
        transfer=transfer,
        inventory_item_id=payload.inventory_item_id,
        batch_id=payload.batch_id,
        quantity=payload.quantity,
        notes=payload.notes,
    )
    return DataResponse(data=TransferItemOut.model_validate(item), meta=request_meta(request))


@router.post("/transfers/{transfer_id}/post")
async def post_transfer(
    request: Request,
    transfer_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.transfers.post")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TransferOut]:
    transfer = await _get_transfer_or_404(session, transfer_id)
    transfer = await transfers.post_transfer(
        session, actor=actor, transfer=transfer, request=request
    )
    out = await _build_transfer_out(session, transfer)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/transfers/{transfer_id}/reverse")
async def reverse_transfer(
    request: Request,
    transfer_id: uuid.UUID,
    payload: TransferReverseIn,
    actor: StaffUser = Depends(require_permission("inventory.transfers.reverse")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[TransferOut]:
    transfer = await _get_transfer_or_404(session, transfer_id)
    transfer = await transfers.reverse_transfer(
        session, actor=actor, transfer=transfer, reason=payload.reason, request=request
    )
    out = await _build_transfer_out(session, transfer)
    return DataResponse(data=out, meta=request_meta(request))


# --- Stock counts --------------------------------------------------------------------


@router.get("/counts")
async def list_counts(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    status_filter: str | None = Query(default=None, alias="status"),
    storage_location_id: uuid.UUID | None = Query(default=None),
) -> PaginatedResponse[StockCountListItemOut]:
    stmt = select(StockCount)
    count_stmt = select(func.count()).select_from(StockCount)
    if status_filter:
        stmt, count_stmt = (
            stmt.where(StockCount.status == status_filter),
            count_stmt.where(StockCount.status == status_filter),
        )
    if storage_location_id:
        clause = StockCount.storage_location_id == storage_location_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(StockCount.created_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[StockCountListItemOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


async def _get_count_or_404(session: AsyncSession, count_id: uuid.UUID) -> StockCount:
    count = await session.get(StockCount, count_id)
    if count is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock count not found.")
    return count


async def _build_count_out(session: AsyncSession, count: StockCount) -> StockCountOut:
    lines = (
        await session.scalars(select(StockCountLine).where(StockCountLine.count_id == count.id))
    ).all()
    return StockCountOut.model_validate(count).model_copy(
        update={"lines": [StockCountLineOut.model_validate(line) for line in lines]}
    )


@router.post("/counts", status_code=status.HTTP_201_CREATED)
async def create_count(
    request: Request,
    payload: StockCountCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.counts.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StockCountOut]:
    count = await stock_counts.create_count(
        session,
        actor=actor,
        storage_location_id=payload.storage_location_id,
        scheduled_date=payload.scheduled_date,
        notes=payload.notes,
    )
    out = await _build_count_out(session, count)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/counts/{count_id}")
async def get_count(
    request: Request,
    count_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StockCountOut]:
    count = await _get_count_or_404(session, count_id)
    out = await _build_count_out(session, count)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/counts/{count_id}/start")
async def start_count(
    request: Request,
    count_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.counts.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StockCountOut]:
    count = await _get_count_or_404(session, count_id)
    count = await stock_counts.start_count(session, actor=actor, count=count)
    out = await _build_count_out(session, count)
    return DataResponse(data=out, meta=request_meta(request))


@router.patch("/counts/{count_id}/lines/{line_id}")
async def record_count_line(
    request: Request,
    count_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: StockCountLineRecordIn,
    actor: StaffUser = Depends(require_permission("inventory.counts.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StockCountLineOut]:
    count = await _get_count_or_404(session, count_id)
    line = await session.get(StockCountLine, line_id)
    if line is None or line.count_id != count.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Count line not found.")
    line = await stock_counts.record_count_line(
        session,
        count=count,
        line=line,
        counted_quantity=payload.counted_quantity,
        reason=payload.reason,
        notes=payload.notes,
    )
    return DataResponse(data=StockCountLineOut.model_validate(line), meta=request_meta(request))


@router.post("/counts/{count_id}/submit")
async def submit_count(
    request: Request,
    count_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.counts.submit")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StockCountOut]:
    count = await _get_count_or_404(session, count_id)
    count = await stock_counts.submit_count(session, actor=actor, count=count, request=request)
    out = await _build_count_out(session, count)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/counts/{count_id}/approve")
async def approve_count(
    request: Request,
    count_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.counts.approve")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StockCountOut]:
    count = await _get_count_or_404(session, count_id)
    count = await stock_counts.approve_count(session, actor=actor, count=count, request=request)
    out = await _build_count_out(session, count)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/counts/{count_id}/cancel")
async def cancel_count(
    request: Request,
    count_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.counts.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[StockCountOut]:
    count = await _get_count_or_404(session, count_id)
    count = await stock_counts.cancel_count(session, actor=actor, count=count, request=request)
    out = await _build_count_out(session, count)
    return DataResponse(data=out, meta=request_meta(request))


# --- Recipes --------------------------------------------------------------------------


@router.get("/recipes")
async def list_recipes(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.recipes.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    product_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> PaginatedResponse[RecipeListItemOut]:
    stmt = select(Recipe).where(Recipe.deleted_at.is_(None))
    count_stmt = select(func.count()).select_from(Recipe).where(Recipe.deleted_at.is_(None))
    if product_id:
        clause = Recipe.product_id == product_id
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    if is_active is not None:
        clause = Recipe.is_active == is_active
        stmt, count_stmt = stmt.where(clause), count_stmt.where(clause)
    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(Recipe.created_at.desc())
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    return PaginatedResponse(
        data=[RecipeListItemOut.model_validate(r) for r in rows],
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


async def _get_recipe_or_404(session: AsyncSession, recipe_id: uuid.UUID) -> Recipe:
    recipe = await session.get(Recipe, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipe not found.")
    return recipe


async def _build_recipe_out(session: AsyncSession, recipe: Recipe) -> RecipeOut:
    items = (
        await session.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id))
    ).all()
    return RecipeOut.model_validate(recipe).model_copy(
        update={"items": [RecipeItemOut.model_validate(i) for i in items]}
    )


@router.get("/recipes/resolve")
async def resolve_recipe_endpoint(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.recipes.view")),
    session: AsyncSession = Depends(get_db),
    product_id: uuid.UUID = Query(...),
    variant_id: uuid.UUID | None = Query(default=None),
) -> DataResponse[RecipeOut | None]:
    recipe = await recipe_service.resolve_recipe(
        session, product_id=product_id, variant_id=variant_id, as_of=datetime.now(UTC)
    )
    if recipe is None:
        return DataResponse(data=None, meta=request_meta(request))
    out = await _build_recipe_out(session, recipe)
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/recipes", status_code=status.HTTP_201_CREATED)
async def create_recipe(
    request: Request,
    payload: RecipeCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.recipes.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecipeOut]:
    recipe = await recipe_service.create_recipe(
        session,
        actor=actor,
        product_id=payload.product_id,
        variant_id=payload.variant_id,
        yield_quantity=payload.yield_quantity,
        yield_unit_id=payload.yield_unit_id,
        preparation_loss_percentage=payload.preparation_loss_percentage,
        effective_from=payload.effective_from or datetime.now(UTC),
        notes=payload.notes,
    )
    for item_in in payload.items:
        await recipe_service.add_recipe_item(
            session,
            recipe=recipe,
            inventory_item_id=item_in.inventory_item_id,
            quantity_required=item_in.quantity_required,
            unit_id=item_in.unit_id,
            waste_factor=item_in.waste_factor,
            storage_location_id=item_in.storage_location_id,
            display_order=item_in.display_order,
            notes=item_in.notes,
        )
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="inventory.recipe.created",
        target_type="recipe",
        target_id=recipe.id,
        request=request,
        safe_metadata={"recipe_code": recipe.recipe_code, "product_id": str(recipe.product_id)},
    )
    out = await _build_recipe_out(session, recipe)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/recipes/{recipe_id}")
async def get_recipe(
    request: Request,
    recipe_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.recipes.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecipeOut]:
    recipe = await _get_recipe_or_404(session, recipe_id)
    out = await _build_recipe_out(session, recipe)
    return DataResponse(data=out, meta=request_meta(request))


@router.get("/recipes/{recipe_id}/cost")
async def get_recipe_cost(
    request: Request,
    recipe_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("inventory.cost.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecipeCostOut]:
    recipe = await _get_recipe_or_404(session, recipe_id)
    cost = await recipe_service.calculate_recipe_cost(session, recipe=recipe)
    out = RecipeCostOut(
        recipe_id=cost.recipe_id,
        ingredients=[
            IngredientCostOut(
                recipe_item_id=i.recipe_item_id,
                inventory_item_id=i.inventory_item_id,
                inventory_item_name=i.inventory_item_name,
                base_quantity=i.base_quantity,
                effective_quantity=i.effective_quantity,
                unit_cost_minor=i.unit_cost_minor,
                cost_minor=i.cost_minor,
                cost_source=i.cost_source,
            )
            for i in cost.ingredients
        ],
        total_ingredient_cost_minor=cost.total_ingredient_cost_minor,
        effective_yield=cost.effective_yield,
        cost_per_yield_minor=cost.cost_per_yield_minor,
        selling_price_minor=cost.selling_price_minor,
        gross_margin_minor=cost.gross_margin_minor,
        gross_margin_percentage=cost.gross_margin_percentage,
        missing_cost_item_names=cost.missing_cost_item_names,
    )
    return DataResponse(data=out, meta=request_meta(request))


@router.post("/recipes/{recipe_id}/items", status_code=status.HTTP_201_CREATED)
async def add_recipe_item(
    request: Request,
    recipe_id: uuid.UUID,
    payload: RecipeItemCreateIn,
    actor: StaffUser = Depends(require_permission("inventory.recipes.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[RecipeItemOut]:
    recipe = await _get_recipe_or_404(session, recipe_id)
    item = await recipe_service.add_recipe_item(
        session,
        recipe=recipe,
        inventory_item_id=payload.inventory_item_id,
        quantity_required=payload.quantity_required,
        unit_id=payload.unit_id,
        waste_factor=payload.waste_factor,
        storage_location_id=payload.storage_location_id,
        display_order=payload.display_order,
        notes=payload.notes,
    )
    return DataResponse(data=RecipeItemOut.model_validate(item), meta=request_meta(request))


@router.delete("/recipes/{recipe_id}")
async def archive_recipe(
    request: Request,
    recipe_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("inventory.recipes.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    recipe = await _get_recipe_or_404(session, recipe_id)
    await recipe_service.archive_recipe(session, actor=actor, recipe=recipe, request=request)
    return DataResponse(data={"ok": True}, meta=request_meta(request))


# --- Dashboard ---------------------------------------------------------------------


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    request: Request,
    _actor: StaffUser = Depends(require_permission("inventory.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[InventoryDashboardStatsOut]:
    stats = await dashboard.get_dashboard_stats(session)
    return DataResponse(data=stats, meta=request_meta(request))
