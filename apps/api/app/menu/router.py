import uuid
from datetime import datetime
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PageParams, PaginatedResponse, Pagination
from app.core.responses import DataResponse, request_meta
from app.db.models import (
    MenuCategory,
    Modifier,
    ModifierGroup,
    ModifierGroupItem,
    Product,
    ProductImage,
    ProductModifierGroup,
    ProductVariant,
    StaffUser,
)
from app.db.session import get_db
from app.menu import service
from app.menu.schemas import (
    CategoryCreateIn,
    CategoryOut,
    CategoryReorderIn,
    CategoryUpdateIn,
    ModifierGroupIn,
    ModifierGroupItemIn,
    ModifierGroupItemOut,
    ModifierGroupOut,
    ModifierIn,
    ModifierOut,
    ProductArchiveIn,
    ProductAvailabilityOverrideIn,
    ProductCreateIn,
    ProductImageOut,
    ProductImageReorderIn,
    ProductListItemOut,
    ProductModifierGroupIn,
    ProductModifierGroupOut,
    ProductOut,
    ProductReorderIn,
    ProductUpdateIn,
    ProductVariantIn,
    ProductVariantOut,
)
from app.permissions.dependencies import require_permission
from app.storage.service import MENU_IMAGES_BUCKET, create_signed_url

router = APIRouter(prefix="/api/v1/menu", tags=["menu"])

_CATEGORY_SORT_MAP: dict[str, ColumnElement[Any]] = {
    "sort_order": MenuCategory.sort_order.asc(),
    "name": MenuCategory.name.asc(),
    "created_at": MenuCategory.created_at.desc(),
}
_PRODUCT_SORT_MAP: dict[str, ColumnElement[Any]] = {
    "alphabetical": Product.name.asc(),
    "newest": Product.created_at.desc(),
    "oldest": Product.created_at.asc(),
    "display_order": Product.sort_order.asc(),
    "price": Product.base_price_minor.asc(),
}


async def _get_category_or_404(session: AsyncSession, category_id: uuid.UUID) -> MenuCategory:
    category = await session.get(MenuCategory, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")
    return category


async def _get_product_or_404(session: AsyncSession, product_id: uuid.UUID) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


async def _get_variant_or_404(
    session: AsyncSession, product_id: uuid.UUID, variant_id: uuid.UUID
) -> ProductVariant:
    variant = await session.scalar(
        select(ProductVariant).where(
            ProductVariant.id == variant_id, ProductVariant.product_id == product_id
        )
    )
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found.")
    return variant


async def _get_modifier_group_or_404(session: AsyncSession, group_id: uuid.UUID) -> ModifierGroup:
    group = await session.get(ModifierGroup, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Modifier group not found."
        )
    return group


async def _get_modifier_or_404(session: AsyncSession, modifier_id: uuid.UUID) -> Modifier:
    modifier = await session.get(Modifier, modifier_id)
    if modifier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modifier not found.")
    return modifier


async def _get_image_or_404(
    session: AsyncSession, product_id: uuid.UUID, image_id: uuid.UUID
) -> ProductImage:
    image = await session.scalar(
        select(ProductImage).where(
            ProductImage.id == image_id, ProductImage.product_id == product_id
        )
    )
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found.")
    return image


async def _to_image_out(image: ProductImage) -> ProductImageOut:
    signed_url = await create_signed_url(bucket=MENU_IMAGES_BUCKET, path=image.storage_path)
    return ProductImageOut(
        id=image.id,
        product_id=image.product_id,
        alt_text=image.alt_text,
        sort_order=image.sort_order,
        is_thumbnail=image.is_thumbnail,
        file_size_bytes=image.file_size_bytes,
        mime_type=image.mime_type,
        signed_url=signed_url,
    )


# --- Categories -----------------------------------------------------------


@router.get("/categories")
async def list_categories(
    request: Request,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
    is_active: bool | None = Query(default=None),
    include_archived: bool = Query(default=False),
    sort: str = Query(default="sort_order"),
) -> PaginatedResponse[CategoryOut]:
    if sort not in _CATEGORY_SORT_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort column."
        )

    stmt = select(MenuCategory)
    count_stmt = select(func.count()).select_from(MenuCategory)
    if not include_archived:
        stmt = stmt.where(MenuCategory.deleted_at.is_(None))
        count_stmt = count_stmt.where(MenuCategory.deleted_at.is_(None))
    if search:
        pattern = f"%{search}%"
        clause = or_(MenuCategory.name.ilike(pattern), MenuCategory.code.ilike(pattern))
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if is_active is not None:
        stmt = stmt.where(MenuCategory.is_active == is_active)
        count_stmt = count_stmt.where(MenuCategory.is_active == is_active)

    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(_CATEGORY_SORT_MAP[sort])
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    data = [CategoryOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    request: Request,
    payload: CategoryCreateIn,
    actor: StaffUser = Depends(require_permission("menu.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CategoryOut]:
    category = await service.create_category(session, actor=actor, payload=payload, request=request)
    return DataResponse(data=CategoryOut.model_validate(category), meta=request_meta(request))


@router.get("/categories/{category_id}")
async def get_category(
    request: Request,
    category_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CategoryOut]:
    category = await _get_category_or_404(session, category_id)
    return DataResponse(data=CategoryOut.model_validate(category), meta=request_meta(request))


@router.patch("/categories/{category_id}")
async def update_category(
    request: Request,
    category_id: uuid.UUID,
    payload: CategoryUpdateIn,
    actor: StaffUser = Depends(require_permission("menu.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CategoryOut]:
    category = await _get_category_or_404(session, category_id)
    category = await service.update_category(
        session, actor=actor, category=category, payload=payload, request=request
    )
    return DataResponse(data=CategoryOut.model_validate(category), meta=request_meta(request))


@router.delete("/categories/{category_id}")
async def archive_category(
    request: Request,
    category_id: uuid.UUID,
    payload: ProductArchiveIn,
    actor: StaffUser = Depends(require_permission("menu.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    category = await _get_category_or_404(session, category_id)
    await service.archive_category(
        session, actor=actor, category=category, reason=payload.reason, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/categories/{category_id}/restore")
async def restore_category(
    request: Request,
    category_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[CategoryOut]:
    category = await _get_category_or_404(session, category_id)
    await service.restore_category(session, actor=actor, category=category, request=request)
    return DataResponse(data=CategoryOut.model_validate(category), meta=request_meta(request))


@router.post("/categories/reorder")
async def reorder_categories(
    request: Request,
    payload: CategoryReorderIn,
    actor: StaffUser = Depends(require_permission("menu.categories.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    await service.reorder_categories(
        session,
        actor=actor,
        ordered_category_ids=payload.ordered_category_ids,
        request=request,
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


# --- Products -----------------------------------------------------------


@router.get("/products")
async def list_products(
    request: Request,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
    page_params: PageParams = Depends(),
    search: str | None = Query(default=None, max_length=200),
    category_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    include_archived: bool = Query(default=False),
    is_vegetarian: bool | None = Query(default=None),
    is_vegan: bool | None = Query(default=None),
    is_featured: bool | None = Query(default=None),
    is_available: bool | None = Query(default=None),
    dine_in_available: bool | None = Query(default=None),
    takeaway_available: bool | None = Query(default=None),
    delivery_available: bool | None = Query(default=None),
    tax_category: str | None = Query(default=None),
    sort: str = Query(default="display_order"),
) -> PaginatedResponse[ProductListItemOut]:
    if sort not in _PRODUCT_SORT_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported sort column."
        )

    stmt = select(Product)
    count_stmt = select(func.count()).select_from(Product)
    if not include_archived:
        stmt = stmt.where(Product.deleted_at.is_(None))
        count_stmt = count_stmt.where(Product.deleted_at.is_(None))
    if search:
        pattern = f"%{search}%"
        clause = or_(
            Product.name.ilike(pattern),
            Product.product_code.ilike(pattern),
            Product.barcode.ilike(pattern),
        )
        stmt = stmt.where(clause)
        count_stmt = count_stmt.where(clause)
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
        count_stmt = count_stmt.where(Product.category_id == category_id)
    if is_active is not None:
        stmt = stmt.where(Product.is_active == is_active)
        count_stmt = count_stmt.where(Product.is_active == is_active)
    if is_vegetarian is not None:
        food_type = "vegetarian" if is_vegetarian else "non_vegetarian"
        stmt = stmt.where(Product.food_type == food_type)
        count_stmt = count_stmt.where(Product.food_type == food_type)
    if is_vegan is not None:
        stmt = stmt.where(Product.is_vegan_capable == is_vegan)
        count_stmt = count_stmt.where(Product.is_vegan_capable == is_vegan)
    if is_featured is not None:
        stmt = stmt.where(Product.is_featured == is_featured)
        count_stmt = count_stmt.where(Product.is_featured == is_featured)
    if is_available is not None:
        stmt = stmt.where(Product.is_available == is_available)
        count_stmt = count_stmt.where(Product.is_available == is_available)
    if dine_in_available is not None:
        stmt = stmt.where(Product.dine_in_available == dine_in_available)
        count_stmt = count_stmt.where(Product.dine_in_available == dine_in_available)
    if takeaway_available is not None:
        stmt = stmt.where(Product.takeaway_available == takeaway_available)
        count_stmt = count_stmt.where(Product.takeaway_available == takeaway_available)
    if delivery_available is not None:
        stmt = stmt.where(Product.delivery_available == delivery_available)
        count_stmt = count_stmt.where(Product.delivery_available == delivery_available)
    if tax_category:
        stmt = stmt.where(Product.tax_category == tax_category)
        count_stmt = count_stmt.where(Product.tax_category == tax_category)

    total = await session.scalar(count_stmt) or 0
    stmt = (
        stmt.order_by(_PRODUCT_SORT_MAP[sort])
        .offset((page_params.page - 1) * page_params.page_size)
        .limit(page_params.page_size)
    )
    rows = (await session.scalars(stmt)).all()
    data = [ProductListItemOut.model_validate(row) for row in rows]
    return PaginatedResponse(
        data=data,
        pagination=Pagination(page=page_params.page, page_size=page_params.page_size, total=total),
        meta=request_meta(request),
    )


@router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_product(
    request: Request,
    payload: ProductCreateIn,
    actor: StaffUser = Depends(require_permission("menu.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductOut]:
    product = await service.create_product(session, actor=actor, payload=payload, request=request)
    return DataResponse(data=ProductOut.model_validate(product), meta=request_meta(request))


@router.get("/products/{product_id}")
async def get_product(
    request: Request,
    product_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductOut]:
    product = await _get_product_or_404(session, product_id)
    return DataResponse(data=ProductOut.model_validate(product), meta=request_meta(request))


@router.patch("/products/{product_id}")
async def update_product(
    request: Request,
    product_id: uuid.UUID,
    payload: ProductUpdateIn,
    actor: StaffUser = Depends(require_permission("menu.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductOut]:
    product = await _get_product_or_404(session, product_id)
    product = await service.update_product(
        session, actor=actor, product=product, payload=payload, request=request
    )
    return DataResponse(data=ProductOut.model_validate(product), meta=request_meta(request))


@router.delete("/products/{product_id}")
async def archive_product(
    request: Request,
    product_id: uuid.UUID,
    payload: ProductArchiveIn,
    actor: StaffUser = Depends(require_permission("menu.archive")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    product = await _get_product_or_404(session, product_id)
    await service.archive_product(
        session, actor=actor, product=product, reason=payload.reason, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/products/{product_id}/restore")
async def restore_product(
    request: Request,
    product_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.restore")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductOut]:
    product = await session.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    await service.restore_product(session, actor=actor, product=product, request=request)
    return DataResponse(data=ProductOut.model_validate(product), meta=request_meta(request))


@router.post("/products/{product_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_product(
    request: Request,
    product_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.create")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductOut]:
    product = await _get_product_or_404(session, product_id)
    duplicate = await service.duplicate_product(
        session, actor=actor, product=product, request=request
    )
    return DataResponse(data=ProductOut.model_validate(duplicate), meta=request_meta(request))


@router.post("/products/{product_id}/availability-override")
async def set_availability_override(
    request: Request,
    product_id: uuid.UUID,
    payload: ProductAvailabilityOverrideIn,
    actor: StaffUser = Depends(require_permission("menu.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductOut]:
    product = await _get_product_or_404(session, product_id)
    until = datetime.fromisoformat(payload.until) if payload.until else None
    product = await service.set_availability_override(
        session,
        actor=actor,
        product=product,
        is_available=payload.is_available,
        reason=payload.reason,
        until=until,
        request=request,
    )
    return DataResponse(data=ProductOut.model_validate(product), meta=request_meta(request))


@router.post("/products/reorder")
async def reorder_products(
    request: Request,
    payload: ProductReorderIn,
    actor: StaffUser = Depends(require_permission("menu.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    await service.reorder_products(
        session, actor=actor, ordered_product_ids=payload.ordered_product_ids, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


# --- Variants -----------------------------------------------------------


@router.get("/products/{product_id}/variants")
async def list_variants(
    request: Request,
    product_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ProductVariantOut]]:
    await _get_product_or_404(session, product_id)
    rows = (
        await session.scalars(
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id, ProductVariant.deleted_at.is_(None))
            .order_by(ProductVariant.sort_order)
        )
    ).all()
    data = [ProductVariantOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/products/{product_id}/variants", status_code=status.HTTP_201_CREATED)
async def add_variant(
    request: Request,
    product_id: uuid.UUID,
    payload: ProductVariantIn,
    actor: StaffUser = Depends(require_permission("menu.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductVariantOut]:
    product = await _get_product_or_404(session, product_id)
    variant = await service.add_variant(
        session, actor=actor, product=product, payload=payload, request=request
    )
    return DataResponse(data=ProductVariantOut.model_validate(variant), meta=request_meta(request))


@router.patch("/products/{product_id}/variants/{variant_id}")
async def update_variant(
    request: Request,
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    payload: ProductVariantIn,
    actor: StaffUser = Depends(require_permission("menu.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductVariantOut]:
    variant = await _get_variant_or_404(session, product_id, variant_id)
    variant = await service.update_variant(
        session, actor=actor, variant=variant, payload=payload.model_dump(), request=request
    )
    return DataResponse(data=ProductVariantOut.model_validate(variant), meta=request_meta(request))


@router.delete("/products/{product_id}/variants/{variant_id}")
async def archive_variant(
    request: Request,
    product_id: uuid.UUID,
    variant_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.update")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    variant = await _get_variant_or_404(session, product_id, variant_id)
    await service.archive_variant(session, actor=actor, variant=variant, request=request)
    return DataResponse(data={"ok": True}, meta=request_meta(request))


# --- Modifier groups and modifiers ------------------------------------------


@router.get("/modifier-groups")
async def list_modifier_groups(
    request: Request,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
    include_archived: bool = Query(default=False),
) -> DataResponse[list[ModifierGroupOut]]:
    stmt = select(ModifierGroup)
    if not include_archived:
        stmt = stmt.where(ModifierGroup.deleted_at.is_(None))
    rows = (await session.scalars(stmt.order_by(ModifierGroup.sort_order))).all()
    data = [ModifierGroupOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/modifier-groups", status_code=status.HTTP_201_CREATED)
async def create_modifier_group(
    request: Request,
    payload: ModifierGroupIn,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ModifierGroupOut]:
    group = await service.create_modifier_group(
        session, actor=actor, payload=payload, request=request
    )
    return DataResponse(data=ModifierGroupOut.model_validate(group), meta=request_meta(request))


@router.patch("/modifier-groups/{group_id}")
async def update_modifier_group(
    request: Request,
    group_id: uuid.UUID,
    payload: ModifierGroupIn,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ModifierGroupOut]:
    group = await _get_modifier_group_or_404(session, group_id)
    group = await service.update_modifier_group(
        session, actor=actor, group=group, payload=payload.model_dump(), request=request
    )
    return DataResponse(data=ModifierGroupOut.model_validate(group), meta=request_meta(request))


@router.delete("/modifier-groups/{group_id}")
async def archive_modifier_group(
    request: Request,
    group_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    group = await _get_modifier_group_or_404(session, group_id)
    await service.archive_modifier_group(session, actor=actor, group=group, request=request)
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/modifier-groups/{group_id}/restore")
async def restore_modifier_group(
    request: Request,
    group_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    group = await _get_modifier_group_or_404(session, group_id)
    await service.restore_modifier_group(session, actor=actor, group=group, request=request)
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.get("/modifier-groups/{group_id}/items")
async def list_modifier_group_items(
    request: Request,
    group_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ModifierGroupItemOut]]:
    await _get_modifier_group_or_404(session, group_id)
    rows = (
        await session.scalars(
            select(ModifierGroupItem)
            .where(ModifierGroupItem.modifier_group_id == group_id)
            .order_by(ModifierGroupItem.sort_order)
        )
    ).all()
    data = [ModifierGroupItemOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/modifier-groups/{group_id}/items", status_code=status.HTTP_201_CREATED)
async def add_modifier_to_group(
    request: Request,
    group_id: uuid.UUID,
    payload: ModifierGroupItemIn,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ModifierGroupItemOut]:
    group = await _get_modifier_group_or_404(session, group_id)
    item = await service.add_modifier_to_group(
        session, actor=actor, group=group, payload=payload, request=request
    )
    return DataResponse(data=ModifierGroupItemOut.model_validate(item), meta=request_meta(request))


@router.delete("/modifier-groups/{group_id}/items/{modifier_id}")
async def remove_modifier_from_group(
    request: Request,
    group_id: uuid.UUID,
    modifier_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    group = await _get_modifier_group_or_404(session, group_id)
    await service.remove_modifier_from_group(
        session, actor=actor, group=group, modifier_id=modifier_id, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.get("/modifiers")
async def list_modifiers(
    request: Request,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
    include_archived: bool = Query(default=False),
) -> DataResponse[list[ModifierOut]]:
    stmt = select(Modifier)
    if not include_archived:
        stmt = stmt.where(Modifier.deleted_at.is_(None))
    rows = (await session.scalars(stmt.order_by(Modifier.name))).all()
    data = [ModifierOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/modifiers", status_code=status.HTTP_201_CREATED)
async def create_modifier(
    request: Request,
    payload: ModifierIn,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ModifierOut]:
    modifier = await service.create_modifier(session, actor=actor, payload=payload, request=request)
    return DataResponse(data=ModifierOut.model_validate(modifier), meta=request_meta(request))


@router.patch("/modifiers/{modifier_id}")
async def update_modifier(
    request: Request,
    modifier_id: uuid.UUID,
    payload: ModifierIn,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ModifierOut]:
    modifier = await _get_modifier_or_404(session, modifier_id)
    modifier = await service.update_modifier(
        session, actor=actor, modifier=modifier, payload=payload.model_dump(), request=request
    )
    return DataResponse(data=ModifierOut.model_validate(modifier), meta=request_meta(request))


@router.delete("/modifiers/{modifier_id}")
async def archive_modifier(
    request: Request,
    modifier_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    modifier = await _get_modifier_or_404(session, modifier_id)
    await service.archive_modifier(session, actor=actor, modifier=modifier, request=request)
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/modifiers/{modifier_id}/restore")
async def restore_modifier(
    request: Request,
    modifier_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    modifier = await _get_modifier_or_404(session, modifier_id)
    await service.restore_modifier(session, actor=actor, modifier=modifier, request=request)
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.get("/products/{product_id}/modifier-groups")
async def list_product_modifier_groups(
    request: Request,
    product_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ProductModifierGroupOut]]:
    await _get_product_or_404(session, product_id)
    rows = (
        await session.scalars(
            select(ProductModifierGroup)
            .where(ProductModifierGroup.product_id == product_id)
            .order_by(ProductModifierGroup.sort_order)
        )
    ).all()
    data = [ProductModifierGroupOut.model_validate(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/products/{product_id}/modifier-groups", status_code=status.HTTP_201_CREATED)
async def attach_modifier_group(
    request: Request,
    product_id: uuid.UUID,
    payload: ProductModifierGroupIn,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductModifierGroupOut]:
    product = await _get_product_or_404(session, product_id)
    mapping = await service.attach_modifier_group(
        session, actor=actor, product=product, payload=payload, request=request
    )
    return DataResponse(
        data=ProductModifierGroupOut.model_validate(mapping), meta=request_meta(request)
    )


@router.delete("/products/{product_id}/modifier-groups/{group_id}")
async def detach_modifier_group(
    request: Request,
    product_id: uuid.UUID,
    group_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.modifiers.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    product = await _get_product_or_404(session, product_id)
    await service.detach_modifier_group(
        session, actor=actor, product=product, modifier_group_id=group_id, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


# --- Images -----------------------------------------------------------


@router.get("/products/{product_id}/images")
async def list_product_images(
    request: Request,
    product_id: uuid.UUID,
    _actor: StaffUser = Depends(require_permission("menu.view")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[list[ProductImageOut]]:
    await _get_product_or_404(session, product_id)
    rows = (
        await session.scalars(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order)
        )
    ).all()
    data = [await _to_image_out(row) for row in rows]
    return DataResponse(data=data, meta=request_meta(request))


@router.post("/products/{product_id}/images", status_code=status.HTTP_201_CREATED)
async def add_product_image(
    request: Request,
    product_id: uuid.UUID,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    actor: StaffUser = Depends(require_permission("menu.images.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductImageOut]:
    product = await _get_product_or_404(session, product_id)
    data = await file.read()
    image = await service.add_product_image(
        session,
        actor=actor,
        product=product,
        data=data,
        filename=file.filename or "upload",
        declared_content_type=file.content_type or "application/octet-stream",
        alt_text=alt_text,
        request=request,
    )
    return DataResponse(data=await _to_image_out(image), meta=request_meta(request))


@router.delete("/products/{product_id}/images/{image_id}")
async def delete_product_image(
    request: Request,
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.images.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    product = await _get_product_or_404(session, product_id)
    image = await _get_image_or_404(session, product_id, image_id)
    await service.delete_product_image(
        session, actor=actor, product=product, image=image, request=request
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/products/{product_id}/images/reorder")
async def reorder_product_images(
    request: Request,
    product_id: uuid.UUID,
    payload: ProductImageReorderIn,
    actor: StaffUser = Depends(require_permission("menu.images.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[dict[str, bool]]:
    product = await _get_product_or_404(session, product_id)
    await service.reorder_product_images(
        session,
        actor=actor,
        product=product,
        ordered_image_ids=payload.ordered_image_ids,
        request=request,
    )
    return DataResponse(data={"ok": True}, meta=request_meta(request))


@router.post("/products/{product_id}/images/{image_id}/set-thumbnail")
async def set_thumbnail(
    request: Request,
    product_id: uuid.UUID,
    image_id: uuid.UUID,
    actor: StaffUser = Depends(require_permission("menu.images.manage")),
    session: AsyncSession = Depends(get_db),
) -> DataResponse[ProductImageOut]:
    product = await _get_product_or_404(session, product_id)
    image = await _get_image_or_404(session, product_id, image_id)
    image = await service.set_thumbnail(
        session, actor=actor, product=product, image=image, request=request
    )
    return DataResponse(data=await _to_image_out(image), meta=request_meta(request))
