import uuid

import pytest
from app.db.models import (
    MenuCategory,
    Modifier,
    ModifierGroup,
    ModifierGroupItem,
    Product,
    ProductImage,
    ProductModifierGroup,
    ProductVariant,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


def _category_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "code": f"cat-{suffix}",
        "name": "Test Category",
    }
    base.update(overrides)
    return base


def _product_kwargs(**overrides: object) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:10]
    base: dict[str, object] = {
        "id": uuid.uuid4(),
        "product_code": f"PROD-{suffix}",
        "name": "Test Product",
        "slug": f"test-product-{suffix}",
        "food_type": "vegetarian",
        "base_price_minor": 10000,
    }
    base.update(overrides)
    return base


async def _make_category(session: AsyncSession) -> MenuCategory:
    category = MenuCategory(**_category_kwargs())
    session.add(category)
    await session.flush()
    return category


async def _make_product(session: AsyncSession, **overrides: object) -> Product:
    if "category_id" not in overrides:
        category = await _make_category(session)
        overrides["category_id"] = category.id
    product = Product(**_product_kwargs(**overrides))
    session.add(product)
    await session.flush()
    return product


# --- MenuCategory -----------------------------------------------------------


async def test_category_rejects_negative_sort_order(db_session: AsyncSession) -> None:
    category = MenuCategory(**_category_kwargs(sort_order=-1))
    db_session.add(category)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_category_code_is_unique(db_session: AsyncSession) -> None:
    code = f"cat-{uuid.uuid4().hex[:10]}"
    db_session.add(MenuCategory(**_category_kwargs(code=code)))
    await db_session.flush()

    db_session.add(MenuCategory(**_category_kwargs(code=code)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_category_defaults(db_session: AsyncSession) -> None:
    category = MenuCategory(**_category_kwargs())
    db_session.add(category)
    await db_session.flush()
    assert category.is_active is True
    assert category.sort_order == 0


# --- Product ------------------------------------------------------------


async def test_product_rejects_invalid_food_type(db_session: AsyncSession) -> None:
    category = await _make_category(db_session)
    product = Product(**_product_kwargs(category_id=category.id, food_type="omnivore"))
    db_session.add(product)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_rejects_invalid_availability_source(db_session: AsyncSession) -> None:
    category = await _make_category(db_session)
    product = Product(
        **_product_kwargs(category_id=category.id, availability_source="bogus_source")
    )
    db_session.add(product)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_rejects_invalid_spice_level(db_session: AsyncSession) -> None:
    category = await _make_category(db_session)
    product = Product(**_product_kwargs(category_id=category.id, spice_level="nuclear"))
    db_session.add(product)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_rejects_negative_base_price(db_session: AsyncSession) -> None:
    category = await _make_category(db_session)
    product = Product(**_product_kwargs(category_id=category.id, base_price_minor=-100))
    db_session.add(product)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_rejects_negative_preparation_minutes(db_session: AsyncSession) -> None:
    category = await _make_category(db_session)
    product = Product(**_product_kwargs(category_id=category.id, preparation_minutes=-5))
    db_session.add(product)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_rejects_negative_calories(db_session: AsyncSession) -> None:
    category = await _make_category(db_session)
    product = Product(**_product_kwargs(category_id=category.id, calories=-1))
    db_session.add(product)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_code_is_unique(db_session: AsyncSession) -> None:
    category = await _make_category(db_session)
    code = f"PROD-{uuid.uuid4().hex[:10]}"
    db_session.add(Product(**_product_kwargs(category_id=category.id, product_code=code)))
    await db_session.flush()

    db_session.add(Product(**_product_kwargs(category_id=category.id, product_code=code)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_slug_is_unique(db_session: AsyncSession) -> None:
    category = await _make_category(db_session)
    slug = f"dup-slug-{uuid.uuid4().hex[:8]}"
    db_session.add(Product(**_product_kwargs(category_id=category.id, slug=slug)))
    await db_session.flush()

    db_session.add(Product(**_product_kwargs(category_id=category.id, slug=slug)))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_requires_a_real_category(db_session: AsyncSession) -> None:
    product = Product(**_product_kwargs(category_id=uuid.uuid4()))
    db_session.add(product)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_defaults(db_session: AsyncSession) -> None:
    product = await _make_product(db_session)
    assert product.is_active is True
    assert product.is_available is True
    assert product.availability_source == "manual"
    assert product.is_jain_capable is False
    assert product.is_featured is False


# --- ProductVariant -----------------------------------------------------


async def test_variant_rejects_negative_price(db_session: AsyncSession) -> None:
    product = await _make_product(db_session)
    variant = ProductVariant(
        id=uuid.uuid4(),
        product_id=product.id,
        code=f"var-{uuid.uuid4().hex[:8]}",
        name="Small",
        price_minor=-100,
    )
    db_session.add(variant)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_variant_code_is_unique(db_session: AsyncSession) -> None:
    product = await _make_product(db_session)
    code = f"var-{uuid.uuid4().hex[:8]}"
    db_session.add(
        ProductVariant(id=uuid.uuid4(), product_id=product.id, code=code, name="A", price_minor=100)
    )
    await db_session.flush()

    db_session.add(
        ProductVariant(id=uuid.uuid4(), product_id=product.id, code=code, name="B", price_minor=200)
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- ProductImage ---------------------------------------------------------


async def test_image_rejects_non_positive_file_size(db_session: AsyncSession) -> None:
    product = await _make_product(db_session)
    image = ProductImage(
        id=uuid.uuid4(),
        product_id=product.id,
        storage_path="products/x/y.jpg",
        file_size_bytes=0,
        mime_type="image/jpeg",
    )
    db_session.add(image)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_only_one_thumbnail_per_product(db_session: AsyncSession) -> None:
    product = await _make_product(db_session)
    db_session.add(
        ProductImage(
            id=uuid.uuid4(),
            product_id=product.id,
            storage_path="products/x/a.jpg",
            file_size_bytes=100,
            mime_type="image/jpeg",
            is_thumbnail=True,
        )
    )
    await db_session.flush()

    db_session.add(
        ProductImage(
            id=uuid.uuid4(),
            product_id=product.id,
            storage_path="products/x/b.jpg",
            file_size_bytes=100,
            mime_type="image/jpeg",
            is_thumbnail=True,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- ModifierGroup and Modifier -------------------------------------------


async def test_modifier_group_rejects_max_select_below_one(db_session: AsyncSession) -> None:
    group = ModifierGroup(id=uuid.uuid4(), name="Test Group", max_select=0)
    db_session.add(group)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_modifier_group_rejects_max_below_min(db_session: AsyncSession) -> None:
    group = ModifierGroup(id=uuid.uuid4(), name="Test Group", min_select=3, max_select=1)
    db_session.add(group)
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_modifier_group_defaults(db_session: AsyncSession) -> None:
    group = ModifierGroup(id=uuid.uuid4(), name="Test Group")
    db_session.add(group)
    await db_session.flush()
    assert group.min_select == 0
    assert group.max_select == 1
    assert group.is_required is False


async def test_modifier_rejects_negative_default_price(db_session: AsyncSession) -> None:
    modifier = Modifier(id=uuid.uuid4(), name="Test Modifier", default_price_minor=-1)
    db_session.add(modifier)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# --- Mapping tables -------------------------------------------------------


async def test_modifier_group_item_rejects_duplicate_mapping(db_session: AsyncSession) -> None:
    group = ModifierGroup(id=uuid.uuid4(), name="Test Group")
    modifier = Modifier(id=uuid.uuid4(), name="Test Modifier")
    db_session.add_all([group, modifier])
    await db_session.flush()

    db_session.add(ModifierGroupItem(modifier_group_id=group.id, modifier_id=modifier.id))
    await db_session.flush()

    db_session.add(ModifierGroupItem(modifier_group_id=group.id, modifier_id=modifier.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_modifier_group_item_rejects_negative_price_override(
    db_session: AsyncSession,
) -> None:
    group = ModifierGroup(id=uuid.uuid4(), name="Test Group")
    modifier = Modifier(id=uuid.uuid4(), name="Test Modifier")
    db_session.add_all([group, modifier])
    await db_session.flush()

    db_session.add(
        ModifierGroupItem(
            modifier_group_id=group.id, modifier_id=modifier.id, price_minor_override=-50
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_product_modifier_group_rejects_duplicate_mapping(db_session: AsyncSession) -> None:
    product = await _make_product(db_session)
    group = ModifierGroup(id=uuid.uuid4(), name="Test Group")
    db_session.add(group)
    await db_session.flush()

    db_session.add(ProductModifierGroup(product_id=product.id, modifier_group_id=group.id))
    await db_session.flush()

    db_session.add(ProductModifierGroup(product_id=product.id, modifier_group_id=group.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()
