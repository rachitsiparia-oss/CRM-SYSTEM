"""Menu and product business logic — CORE_CRM_MODULES.md section 7,
DATABASE_AND_API.md section 8. Kept out of the router for the same reason
as app.customers.service and app.leads.service (Phase 5 precedent):
duplicate/reorder/image-sync behavior needs to be unit-testable without an
HTTP client.
"""

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_audit_event
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
from app.menu.schemas import (
    CategoryCreateIn,
    CategoryUpdateIn,
    ModifierGroupIn,
    ModifierGroupItemIn,
    ModifierIn,
    ProductCreateIn,
    ProductModifierGroupIn,
    ProductUpdateIn,
    ProductVariantIn,
)
from app.storage.service import MENU_IMAGES_BUCKET, build_object_path, delete_object, upload_object
from app.storage.validation import ImageValidationError, validate_image_upload

_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def generate_product_code() -> str:
    return f"PROD-{uuid.uuid4().hex[:8].upper()}"


def slugify(name: str) -> str:
    slug = _SLUG_PATTERN.sub("-", name.strip().lower()).strip("-")
    return slug or "product"


async def _unique_slug(
    session: AsyncSession, *, base_slug: str, exclude_id: uuid.UUID | None = None
) -> str:
    candidate = base_slug
    suffix = 1
    while True:
        stmt = select(Product.id).where(Product.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        existing = await session.scalar(stmt)
        if existing is None:
            return candidate
        suffix += 1
        candidate = f"{base_slug}-{suffix}"


# --- Categories -----------------------------------------------------------


async def create_category(
    session: AsyncSession, *, actor: StaffUser, payload: CategoryCreateIn, request: Request | None
) -> MenuCategory:
    existing = await session.scalar(select(MenuCategory).where(MenuCategory.code == payload.code))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A category with this code already exists."
        )

    category = MenuCategory(
        id=uuid.uuid4(),
        code=payload.code,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        created_by=actor.id,
    )
    session.add(category)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="menu_category.created",
        target_type="menu_category",
        target_id=category.id,
        request=request,
        safe_metadata={"code": category.code},
    )
    return category


async def update_category(
    session: AsyncSession,
    *,
    actor: StaffUser,
    category: MenuCategory,
    payload: CategoryUpdateIn,
    request: Request | None,
) -> MenuCategory:
    if payload.expected_version is not None and payload.expected_version != category.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This category was updated by someone else. Reload and try again.",
        )

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    before = {field: getattr(category, field) for field in updates}
    for field, value in updates.items():
        setattr(category, field, value)

    if updates:
        category.version += 1
        category.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="menu_category.updated",
            target_type="menu_category",
            target_id=category.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return category


async def archive_category(
    session: AsyncSession,
    *,
    actor: StaffUser,
    category: MenuCategory,
    reason: str,
    request: Request | None,
) -> None:
    category.deleted_at = datetime.now(UTC)
    category.deleted_by = actor.id
    category.deletion_reason = reason
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="menu_category.archived",
        target_type="menu_category",
        target_id=category.id,
        request=request,
        safe_metadata={"reason": reason},
    )


async def restore_category(
    session: AsyncSession, *, actor: StaffUser, category: MenuCategory, request: Request | None
) -> None:
    category.deleted_at = None
    category.deleted_by = None
    category.deletion_reason = None
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="menu_category.restored",
        target_type="menu_category",
        target_id=category.id,
        request=request,
    )


async def reorder_categories(
    session: AsyncSession,
    *,
    actor: StaffUser,
    ordered_category_ids: list[uuid.UUID],
    request: Request | None,
) -> None:
    categories = (
        await session.scalars(select(MenuCategory).where(MenuCategory.id.in_(ordered_category_ids)))
    ).all()
    by_id = {c.id: c for c in categories}
    missing = [str(cid) for cid in ordered_category_ids if cid not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown category ids: {', '.join(missing)}",
        )
    for index, category_id in enumerate(ordered_category_ids):
        by_id[category_id].sort_order = index
        by_id[category_id].updated_by = actor.id
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="menu_category.reordered",
        target_type="menu_category",
        target_id=None,
        request=request,
        safe_metadata={"count": len(ordered_category_ids)},
    )


# --- Products ---------------------------------------------------------------


async def create_product(
    session: AsyncSession, *, actor: StaffUser, payload: ProductCreateIn, request: Request | None
) -> Product:
    category = await session.get(MenuCategory, payload.category_id)
    if category is None or category.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    product_code = payload.product_code or generate_product_code()
    existing_code = await session.scalar(
        select(Product.id).where(Product.product_code == product_code)
    )
    if existing_code is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This product code is already in use."
        )
    slug = await _unique_slug(session, base_slug=slugify(payload.name))

    fields = payload.model_dump(exclude={"product_code"})
    product = Product(
        id=uuid.uuid4(),
        product_code=product_code,
        slug=slug,
        created_by=actor.id,
        **fields,
    )
    session.add(product)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.created",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={"product_code": product.product_code},
    )
    return product


async def update_product(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    payload: ProductUpdateIn,
    request: Request | None,
) -> Product:
    if payload.expected_version is not None and payload.expected_version != product.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product was updated by someone else. Reload and try again.",
        )

    updates = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
    if "category_id" in updates:
        category = await session.get(MenuCategory, updates["category_id"])
        if category is None or category.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

    before = {field: getattr(product, field) for field in updates}
    for field, value in updates.items():
        setattr(product, field, value)
    if "name" in updates:
        product.slug = await _unique_slug(
            session, base_slug=slugify(product.name), exclude_id=product.id
        )
    if any(field in updates for field in ("is_active", "is_available")):
        product.availability_source = "manual"

    if updates:
        product.version += 1
        product.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="product.updated",
            target_type="product",
            target_id=product.id,
            request=request,
            before_summary=before,
            after_summary=updates,
        )
    return product


async def duplicate_product(
    session: AsyncSession, *, actor: StaffUser, product: Product, request: Request | None
) -> Product:
    """Copies core fields, variants, and modifier-group mappings —
    everything staff typically want when spinning up a seasonal or
    near-identical item. Images are never copied: they point at specific
    uploaded files tied to the original product's gallery, and copying the
    storage reference without copying the bytes would leave two products
    silently sharing (and able to independently delete) the same object.
    """
    new_code = generate_product_code()
    new_slug = await _unique_slug(session, base_slug=f"{product.slug}-copy")

    duplicate = Product(
        id=uuid.uuid4(),
        product_code=new_code,
        category_id=product.category_id,
        name=f"{product.name} (Copy)",
        display_name=product.display_name,
        slug=new_slug,
        description=product.description,
        short_description=product.short_description,
        food_type=product.food_type,
        is_jain_capable=product.is_jain_capable,
        is_vegan_capable=product.is_vegan_capable,
        contains_egg=product.contains_egg,
        contains_dairy=product.contains_dairy,
        contains_gluten=product.contains_gluten,
        contains_nuts=product.contains_nuts,
        contains_soy=product.contains_soy,
        contains_alcohol=product.contains_alcohol,
        spice_level=product.spice_level,
        preparation_minutes=product.preparation_minutes,
        calories=product.calories,
        base_price_minor=product.base_price_minor,
        tax_category=product.tax_category,
        # Duplicates start inactive/unavailable so a half-configured copy
        # (no images yet, name still says "(Copy)") can never be sold
        # before staff review it.
        is_active=False,
        is_available=False,
        dine_in_available=product.dine_in_available,
        takeaway_available=product.takeaway_available,
        delivery_available=product.delivery_available,
        sort_order=product.sort_order,
        is_featured=False,
        is_chef_recommended=False,
        created_by=actor.id,
    )
    session.add(duplicate)
    await session.flush()

    variants = (
        await session.scalars(
            select(ProductVariant).where(
                ProductVariant.product_id == product.id, ProductVariant.deleted_at.is_(None)
            )
        )
    ).all()
    for variant in variants:
        session.add(
            ProductVariant(
                id=uuid.uuid4(),
                product_id=duplicate.id,
                code=f"{variant.code}-COPY-{uuid.uuid4().hex[:6].upper()}",
                name=variant.name,
                price_minor=variant.price_minor,
                sort_order=variant.sort_order,
                is_active=variant.is_active,
                is_available=variant.is_available,
                preparation_minutes=variant.preparation_minutes,
                created_by=actor.id,
            )
        )

    mappings = (
        await session.scalars(
            select(ProductModifierGroup).where(ProductModifierGroup.product_id == product.id)
        )
    ).all()
    for mapping in mappings:
        session.add(
            ProductModifierGroup(
                product_id=duplicate.id,
                modifier_group_id=mapping.modifier_group_id,
                sort_order=mapping.sort_order,
                created_by=actor.id,
            )
        )

    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.duplicated",
        target_type="product",
        target_id=duplicate.id,
        request=request,
        safe_metadata={
            "source_product_id": str(product.id),
            "variants_copied": len(variants),
            "modifier_groups_copied": len(mappings),
        },
    )
    return duplicate


async def set_availability_override(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    is_available: bool,
    reason: str,
    until: datetime | None,
    request: Request | None,
) -> Product:
    """CORE_CRM_MODULES.md section 7.8's manual-override requirements:
    authorized user (permission-checked by the router), reason, expiry
    time, and audit log."""
    before_available = product.is_available
    product.is_available = is_available
    product.availability_source = "override"
    product.manual_override_until = until
    product.manual_override_reason = reason
    product.updated_by = actor.id
    product.version += 1
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.availability_overridden",
        target_type="product",
        target_id=product.id,
        request=request,
        before_summary={"is_available": before_available},
        after_summary={"is_available": is_available},
        safe_metadata={"reason": reason, "until": until.isoformat() if until else None},
    )
    return product


async def archive_product(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    reason: str,
    request: Request | None,
) -> None:
    product.deleted_at = datetime.now(UTC)
    product.deleted_by = actor.id
    product.deletion_reason = reason
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.archived",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={"reason": reason},
    )


async def restore_product(
    session: AsyncSession, *, actor: StaffUser, product: Product, request: Request | None
) -> None:
    product.deleted_at = None
    product.deleted_by = None
    product.deletion_reason = None
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.restored",
        target_type="product",
        target_id=product.id,
        request=request,
    )


async def reorder_products(
    session: AsyncSession,
    *,
    actor: StaffUser,
    ordered_product_ids: list[uuid.UUID],
    request: Request | None,
) -> None:
    products = (
        await session.scalars(select(Product).where(Product.id.in_(ordered_product_ids)))
    ).all()
    by_id = {p.id: p for p in products}
    missing = [str(pid) for pid in ordered_product_ids if pid not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown product ids: {', '.join(missing)}",
        )
    for index, product_id in enumerate(ordered_product_ids):
        by_id[product_id].sort_order = index
        by_id[product_id].updated_by = actor.id
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.reordered",
        target_type="product",
        target_id=None,
        request=request,
        safe_metadata={"count": len(ordered_product_ids)},
    )


# --- Variants ---------------------------------------------------------------


async def add_variant(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    payload: ProductVariantIn,
    request: Request | None,
) -> ProductVariant:
    existing = await session.scalar(
        select(ProductVariant.id).where(ProductVariant.code == payload.code)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This variant code is already in use."
        )
    variant = ProductVariant(
        id=uuid.uuid4(), product_id=product.id, created_by=actor.id, **payload.model_dump()
    )
    session.add(variant)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.variant_added",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={"variant_id": str(variant.id), "code": variant.code},
    )
    return variant


async def update_variant(
    session: AsyncSession,
    *,
    actor: StaffUser,
    variant: ProductVariant,
    payload: dict[str, Any],
    request: Request | None,
) -> ProductVariant:
    before = {field: getattr(variant, field) for field in payload}
    for field, value in payload.items():
        setattr(variant, field, value)
    if payload:
        variant.version += 1
        variant.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="product.variant_updated",
            target_type="product",
            target_id=variant.product_id,
            request=request,
            before_summary=before,
            after_summary=payload,
            safe_metadata={"variant_id": str(variant.id)},
        )
    return variant


async def archive_variant(
    session: AsyncSession, *, actor: StaffUser, variant: ProductVariant, request: Request | None
) -> None:
    variant.deleted_at = datetime.now(UTC)
    variant.deleted_by = actor.id
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.variant_archived",
        target_type="product",
        target_id=variant.product_id,
        request=request,
        safe_metadata={"variant_id": str(variant.id)},
    )


# --- Modifier groups and modifiers ------------------------------------------


async def create_modifier_group(
    session: AsyncSession, *, actor: StaffUser, payload: ModifierGroupIn, request: Request | None
) -> ModifierGroup:
    group = ModifierGroup(id=uuid.uuid4(), created_by=actor.id, **payload.model_dump())
    session.add(group)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="modifier_group.created",
        target_type="modifier_group",
        target_id=group.id,
        request=request,
    )
    return group


async def update_modifier_group(
    session: AsyncSession,
    *,
    actor: StaffUser,
    group: ModifierGroup,
    payload: dict[str, Any],
    request: Request | None,
) -> ModifierGroup:
    before = {field: getattr(group, field) for field in payload}
    for field, value in payload.items():
        setattr(group, field, value)
    if payload:
        group.version += 1
        group.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="modifier_group.updated",
            target_type="modifier_group",
            target_id=group.id,
            request=request,
            before_summary=before,
            after_summary=payload,
        )
    return group


async def archive_modifier_group(
    session: AsyncSession, *, actor: StaffUser, group: ModifierGroup, request: Request | None
) -> None:
    group.deleted_at = datetime.now(UTC)
    group.deleted_by = actor.id
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="modifier_group.archived",
        target_type="modifier_group",
        target_id=group.id,
        request=request,
    )


async def restore_modifier_group(
    session: AsyncSession, *, actor: StaffUser, group: ModifierGroup, request: Request | None
) -> None:
    group.deleted_at = None
    group.deleted_by = None
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="modifier_group.restored",
        target_type="modifier_group",
        target_id=group.id,
        request=request,
    )


async def create_modifier(
    session: AsyncSession, *, actor: StaffUser, payload: ModifierIn, request: Request | None
) -> Modifier:
    modifier = Modifier(id=uuid.uuid4(), created_by=actor.id, **payload.model_dump())
    session.add(modifier)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="modifier.created",
        target_type="modifier",
        target_id=modifier.id,
        request=request,
    )
    return modifier


async def update_modifier(
    session: AsyncSession,
    *,
    actor: StaffUser,
    modifier: Modifier,
    payload: dict[str, Any],
    request: Request | None,
) -> Modifier:
    before = {field: getattr(modifier, field) for field in payload}
    for field, value in payload.items():
        setattr(modifier, field, value)
    if payload:
        modifier.version += 1
        modifier.updated_by = actor.id
        await record_audit_event(
            session,
            actor_id=actor.id,
            action_code="modifier.updated",
            target_type="modifier",
            target_id=modifier.id,
            request=request,
            before_summary=before,
            after_summary=payload,
        )
    return modifier


async def archive_modifier(
    session: AsyncSession, *, actor: StaffUser, modifier: Modifier, request: Request | None
) -> None:
    modifier.deleted_at = datetime.now(UTC)
    modifier.deleted_by = actor.id
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="modifier.archived",
        target_type="modifier",
        target_id=modifier.id,
        request=request,
    )


async def restore_modifier(
    session: AsyncSession, *, actor: StaffUser, modifier: Modifier, request: Request | None
) -> None:
    modifier.deleted_at = None
    modifier.deleted_by = None
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="modifier.restored",
        target_type="modifier",
        target_id=modifier.id,
        request=request,
    )


async def add_modifier_to_group(
    session: AsyncSession,
    *,
    actor: StaffUser,
    group: ModifierGroup,
    payload: ModifierGroupItemIn,
    request: Request | None,
) -> ModifierGroupItem:
    modifier = await session.get(Modifier, payload.modifier_id)
    if modifier is None or modifier.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modifier not found.")
    existing = await session.scalar(
        select(ModifierGroupItem).where(
            ModifierGroupItem.modifier_group_id == group.id,
            ModifierGroupItem.modifier_id == payload.modifier_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This modifier is already in the group.",
        )
    item = ModifierGroupItem(
        modifier_group_id=group.id, created_by=actor.id, **payload.model_dump()
    )
    session.add(item)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="modifier_group.item_added",
        target_type="modifier_group",
        target_id=group.id,
        request=request,
        safe_metadata={"modifier_id": str(payload.modifier_id)},
    )
    return item


async def remove_modifier_from_group(
    session: AsyncSession,
    *,
    actor: StaffUser,
    group: ModifierGroup,
    modifier_id: uuid.UUID,
    request: Request | None,
) -> None:
    item = await session.scalar(
        select(ModifierGroupItem).where(
            ModifierGroupItem.modifier_group_id == group.id,
            ModifierGroupItem.modifier_id == modifier_id,
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found.")
    await session.delete(item)
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="modifier_group.item_removed",
        target_type="modifier_group",
        target_id=group.id,
        request=request,
        safe_metadata={"modifier_id": str(modifier_id)},
    )


async def attach_modifier_group(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    payload: ProductModifierGroupIn,
    request: Request | None,
) -> ProductModifierGroup:
    group = await session.get(ModifierGroup, payload.modifier_group_id)
    if group is None or group.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Modifier group not found."
        )
    existing = await session.scalar(
        select(ProductModifierGroup).where(
            ProductModifierGroup.product_id == product.id,
            ProductModifierGroup.modifier_group_id == payload.modifier_group_id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This modifier group is already attached to the product.",
        )
    mapping = ProductModifierGroup(
        product_id=product.id, created_by=actor.id, **payload.model_dump()
    )
    session.add(mapping)
    await session.flush()
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.modifier_group_attached",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={"modifier_group_id": str(payload.modifier_group_id)},
    )
    return mapping


async def detach_modifier_group(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    modifier_group_id: uuid.UUID,
    request: Request | None,
) -> None:
    mapping = await session.scalar(
        select(ProductModifierGroup).where(
            ProductModifierGroup.product_id == product.id,
            ProductModifierGroup.modifier_group_id == modifier_group_id,
        )
    )
    if mapping is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found.")
    await session.delete(mapping)
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.modifier_group_detached",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={"modifier_group_id": str(modifier_group_id)},
    )


# --- Images -------------------------------------------------------------


async def _sync_thumbnail_pointer(session: AsyncSession, *, product: Product) -> None:
    thumbnail = await session.scalar(
        select(ProductImage).where(
            ProductImage.product_id == product.id, ProductImage.is_thumbnail.is_(True)
        )
    )
    product.image_storage_path = thumbnail.storage_path if thumbnail else None


async def add_product_image(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    data: bytes,
    filename: str,
    declared_content_type: str,
    alt_text: str | None,
    request: Request | None,
) -> ProductImage:
    try:
        validated = validate_image_upload(
            data=data, filename=filename, declared_content_type=declared_content_type
        )
    except ImageValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    extension = "." + validated.mime_type.split("/", 1)[1].replace("jpeg", "jpg")
    path = build_object_path(product_id=product.id, filename_extension=extension)
    await upload_object(
        bucket=MENU_IMAGES_BUCKET,
        path=path,
        data=validated.normalized_bytes,
        content_type=validated.mime_type,
    )

    existing_count = await session.scalar(
        select(ProductImage.id).where(ProductImage.product_id == product.id).limit(1)
    )
    is_first_image = existing_count is None

    image = ProductImage(
        id=uuid.uuid4(),
        product_id=product.id,
        storage_path=path,
        alt_text=alt_text,
        sort_order=0,
        is_thumbnail=is_first_image,
        file_size_bytes=validated.file_size_bytes,
        mime_type=validated.mime_type,
        created_by=actor.id,
    )
    session.add(image)
    await session.flush()
    if is_first_image:
        await _sync_thumbnail_pointer(session, product=product)

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.image_added",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={
            "image_id": str(image.id),
            "width": validated.width,
            "height": validated.height,
        },
    )
    return image


async def delete_product_image(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    image: ProductImage,
    request: Request | None,
) -> None:
    was_thumbnail = image.is_thumbnail
    await delete_object(bucket=MENU_IMAGES_BUCKET, path=image.storage_path)
    await session.delete(image)
    await session.flush()

    if was_thumbnail:
        next_image = await session.scalar(
            select(ProductImage)
            .where(ProductImage.product_id == product.id)
            .order_by(ProductImage.sort_order)
            .limit(1)
        )
        if next_image is not None:
            next_image.is_thumbnail = True
        await session.flush()
        await _sync_thumbnail_pointer(session, product=product)

    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.image_removed",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={"image_id": str(image.id)},
    )


async def reorder_product_images(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    ordered_image_ids: list[uuid.UUID],
    request: Request | None,
) -> None:
    images = (
        await session.scalars(
            select(ProductImage).where(
                ProductImage.product_id == product.id, ProductImage.id.in_(ordered_image_ids)
            )
        )
    ).all()
    by_id = {img.id: img for img in images}
    missing = [str(iid) for iid in ordered_image_ids if iid not in by_id]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown image ids: {', '.join(missing)}"
        )
    for index, image_id in enumerate(ordered_image_ids):
        by_id[image_id].sort_order = index
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.images_reordered",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={"count": len(ordered_image_ids)},
    )


async def set_thumbnail(
    session: AsyncSession,
    *,
    actor: StaffUser,
    product: Product,
    image: ProductImage,
    request: Request | None,
) -> ProductImage:
    others = (
        await session.scalars(
            select(ProductImage).where(
                ProductImage.product_id == product.id,
                ProductImage.is_thumbnail.is_(True),
                ProductImage.id != image.id,
            )
        )
    ).all()
    for other in others:
        other.is_thumbnail = False
    # Flushed separately from setting the new thumbnail below: within one
    # flush, SQLAlchemy does not guarantee these two UPDATEs run in the
    # order they were assigned, so the "set new" statement can reach the
    # database before the "clear old" one — which briefly leaves two rows
    # with is_thumbnail=True and trips the one-thumbnail-per-product
    # partial unique index. Clearing first and flushing forces that
    # ordering at the database level.
    await session.flush()
    image.is_thumbnail = True
    await session.flush()
    await _sync_thumbnail_pointer(session, product=product)
    await record_audit_event(
        session,
        actor_id=actor.id,
        action_code="product.thumbnail_changed",
        target_type="product",
        target_id=product.id,
        request=request,
        safe_metadata={"image_id": str(image.id)},
    )
    return image
