"""Idempotent development seed data for the menu catalogue —
PROJECT_PLAN.md section 7 ("Dummy menu catalogue"), DATABASE_AND_API.md
section 8.1's seed category list.

Combos (section 7.8) are seeded as ordinary products in the "Combos"
category with their included items listed in `description` — no
`combo_items` relational table is documented anywhere in
DATABASE_AND_API.md section 8, so a combo is not modeled as a bundle of
other products this phase; it is priced and sold as its own catalogue
entry, matching what is actually specified.

Pizzas use DATABASE_AND_API.md section 8.3's variant pattern directly:
`base_price_minor` is the 8-inch price, with explicit "8-inch"/"11-inch"
`ProductVariant` rows for both documented sizes.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    MenuCategory,
    Modifier,
    ModifierGroup,
    ModifierGroupItem,
    Product,
    ProductModifierGroup,
    ProductVariant,
    StaffUser,
)
from app.menu.service import generate_product_code, slugify

_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("burgers", "Burgers"),
    ("pizzas", "Pizzas"),
    ("tacos", "Tacos"),
    ("burritos-and-bowls", "Burritos and Bowls"),
    ("sides", "Sides"),
    ("beverages", "Beverages"),
    ("desserts", "Desserts"),
    ("combos", "Combos"),
)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    stmt = select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    result = await session.scalar(stmt)
    return result


async def _get_or_create_category(
    session: AsyncSession, *, code: str, name: str, sort_order: int, actor: StaffUser | None
) -> MenuCategory:
    existing = await session.scalar(select(MenuCategory).where(MenuCategory.code == code))
    if existing is not None:
        return existing
    category = MenuCategory(
        id=uuid.uuid4(),
        code=code,
        name=name,
        sort_order=sort_order,
        created_by=actor.id if actor else None,
    )
    session.add(category)
    await session.flush()
    return category


async def _get_or_create_product(
    session: AsyncSession,
    *,
    category: MenuCategory,
    name: str,
    actor: StaffUser | None,
    **fields: object,
) -> tuple[Product, bool]:
    existing = await session.scalar(
        select(Product).where(Product.name == name, Product.category_id == category.id)
    )
    if existing is not None:
        return existing, False

    slug = slugify(name)
    slug_taken = await session.scalar(select(Product.id).where(Product.slug == slug))
    if slug_taken is not None:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

    product = Product(
        id=uuid.uuid4(),
        product_code=generate_product_code(),
        category_id=category.id,
        name=name,
        slug=slug,
        created_by=actor.id if actor else None,
        **fields,
    )
    session.add(product)
    await session.flush()
    return product, True


async def _add_variant(
    session: AsyncSession, *, product: Product, name: str, price_minor: int, sort_order: int
) -> None:
    code = f"{product.product_code}-{slugify(name)}"
    existing = await session.scalar(select(ProductVariant.id).where(ProductVariant.code == code))
    if existing is not None:
        return
    session.add(
        ProductVariant(
            id=uuid.uuid4(),
            product_id=product.id,
            code=code,
            name=name,
            price_minor=price_minor,
            sort_order=sort_order,
        )
    )


async def seed_menu(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    categories = {
        code: await _get_or_create_category(
            session, code=code, name=name, sort_order=i, actor=actor
        )
        for i, (code, name) in enumerate(_CATEGORIES)
    }

    # --- Burgers -------------------------------------------------------
    burgers = categories["burgers"]
    burger_products = []
    for name, price, food_type, prep, calories, jain, description in (
        (
            "RKPR Classic Veg Burger",
            17900,
            "vegetarian",
            12,
            540,
            False,
            "Crispy vegetable patty, lettuce, tomato, onion, pickles, and house burger sauce "
            "in a toasted sesame bun.",
        ),
        (
            "RKPR Spicy Paneer Burger",
            22900,
            "vegetarian",
            14,
            690,
            False,
            "Grilled spicy paneer patty, jalapeños, onion, lettuce, chilli mayonnaise, and cheese.",
        ),
        (
            "Smoky BBQ Chicken Burger",
            25900,
            "non_vegetarian",
            15,
            720,
            False,
            "Grilled chicken patty, smoked barbecue sauce, caramelized onion, lettuce, tomato, "
            "and cheddar.",
        ),
        (
            "Double Crunch Chicken Burger",
            29900,
            "non_vegetarian",
            17,
            920,
            False,
            "Two crispy chicken fillets, cheese, pickles, coleslaw, and spicy house sauce.",
        ),
        (
            "Jain Aloo Crunch Burger",
            18900,
            "vegetarian",
            13,
            510,
            True,
            "Jain-style potato patty without onion or garlic, lettuce, tomato, and Jain mint "
            "sauce.",
        ),
    ):
        product, _ = await _get_or_create_product(
            session,
            category=burgers,
            name=name,
            actor=actor,
            description=description,
            food_type=food_type,
            is_jain_capable=jain,
            preparation_minutes=prep,
            calories=calories,
            base_price_minor=price,
        )
        burger_products.append(product)

    # --- Pizzas (8-inch base price, 11-inch as a variant) ---------------
    pizzas = categories["pizzas"]
    for name, price_8in, price_11in, food_type, description in (
        (
            "Margherita Pizza",
            21900,
            34900,
            "vegetarian",
            "Tomato sauce, mozzarella, basil, and oregano.",
        ),
        (
            "Farmhouse Veg Pizza",
            27900,
            42900,
            "vegetarian",
            "Onion, capsicum, mushroom, sweet corn, tomato, mozzarella, and herbs.",
        ),
        (
            "Paneer Tikka Pizza",
            31900,
            47900,
            "vegetarian",
            "Tandoori paneer, onion, capsicum, mozzarella, and mint drizzle.",
        ),
        (
            "BBQ Chicken Pizza",
            34900,
            52900,
            "non_vegetarian",
            "Barbecue chicken, onion, smoked sauce, mozzarella, and chilli flakes.",
        ),
        (
            "Mexican Fire Pizza",
            32900,
            49900,
            "vegetarian",
            "Jalapeños, black beans, corn, peppers, salsa, cheese, and chipotle sauce.",
        ),
    ):
        product, created = await _get_or_create_product(
            session,
            category=pizzas,
            name=name,
            actor=actor,
            description=description,
            food_type=food_type,
            base_price_minor=price_8in,
        )
        if created:
            await _add_variant(
                session, product=product, name="8-inch", price_minor=price_8in, sort_order=0
            )
            await _add_variant(
                session, product=product, name="11-inch", price_minor=price_11in, sort_order=1
            )

    # --- Tacos -----------------------------------------------------------
    tacos = categories["tacos"]
    for name, price, food_type, description in (
        (
            "Crispy Veg Taco",
            19900,
            "vegetarian",
            "Crispy shells filled with seasoned vegetables, lettuce, salsa, cheese, and sour "
            "cream.",
        ),
        (
            "Paneer Chipotle Taco",
            23900,
            "vegetarian",
            "Grilled paneer, chipotle sauce, cabbage slaw, salsa, and cheese.",
        ),
        (
            "Chicken Salsa Taco",
            25900,
            "non_vegetarian",
            "Spiced chicken, salsa, lettuce, onion, cheese, and lime crema.",
        ),
        (
            "Loaded Bean Taco",
            21900,
            "vegetarian",
            "Black beans, corn, salsa, jalapeños, cheese, and sour cream.",
        ),
    ):
        await _get_or_create_product(
            session,
            category=tacos,
            name=name,
            actor=actor,
            description=f"{description} (Two pieces.)",
            food_type=food_type,
            base_price_minor=price,
        )

    # --- Burritos and bowls ------------------------------------------------
    burritos = categories["burritos-and-bowls"]
    for name, price, food_type, description in (
        (
            "Veg Mexican Burrito",
            24900,
            "vegetarian",
            "Mexican rice, beans, vegetables, salsa, cheese, lettuce, and sour cream.",
        ),
        (
            "Paneer Burrito",
            28900,
            "vegetarian",
            "Paneer, Mexican rice, beans, grilled vegetables, salsa, cheese, and chipotle sauce.",
        ),
        (
            "Chicken Burrito",
            31900,
            "non_vegetarian",
            "Grilled chicken, Mexican rice, beans, salsa, lettuce, cheese, and lime crema.",
        ),
        ("Veg Burrito Bowl", 26900, "vegetarian", "Rice bowl version of the veg burrito."),
        (
            "Chicken Burrito Bowl",
            33900,
            "non_vegetarian",
            "Rice bowl version of the chicken burrito.",
        ),
    ):
        await _get_or_create_product(
            session,
            category=burritos,
            name=name,
            actor=actor,
            description=description,
            food_type=food_type,
            base_price_minor=price,
        )

    # --- Sides -------------------------------------------------------------
    sides = categories["sides"]
    for name, price, food_type in (
        ("Classic Fries", 10900, "vegetarian"),
        ("Peri-Peri Fries", 12900, "vegetarian"),
        ("Loaded Cheese Fries", 18900, "vegetarian"),
        ("Chicken Loaded Fries", 23900, "non_vegetarian"),
        ("Onion Rings", 14900, "vegetarian"),
        ("Garlic Bread", 13900, "vegetarian"),
        ("Cheese Garlic Bread", 17900, "vegetarian"),
        ("Nachos with Salsa", 16900, "vegetarian"),
        ("Loaded Veg Nachos", 22900, "vegetarian"),
        ("Chicken Nuggets", 19900, "non_vegetarian"),
        ("Chicken Wings", 26900, "non_vegetarian"),
    ):
        await _get_or_create_product(
            session,
            category=sides,
            name=name,
            actor=actor,
            food_type=food_type,
            base_price_minor=price,
        )

    # --- Beverages -----------------------------------------------------
    beverages = categories["beverages"]
    for name, price, contains_dairy in (
        ("Classic Cola, 300 ml", 7900, False),
        ("Lemon Soda", 9900, False),
        ("Fresh Lime Water", 8900, False),
        ("Iced Tea", 11900, False),
        ("Cold Coffee", 15900, True),
        ("Chocolate Shake", 17900, True),
        ("Strawberry Shake", 17900, True),
        ("Mango Shake", 17900, True),
        ("Mineral Water, 500 ml", 4000, False),
    ):
        await _get_or_create_product(
            session,
            category=beverages,
            name=name,
            actor=actor,
            food_type="vegetarian",
            contains_dairy=contains_dairy,
            base_price_minor=price,
        )

    # --- Desserts --------------------------------------------------------
    desserts = categories["desserts"]
    for name, price, contains_egg in (
        ("Chocolate Brownie", 15900, False),
        ("Brownie with Vanilla Ice Cream", 21900, False),
        ("Churros with Chocolate Dip", 18900, True),
        ("New York Cheesecake Slice", 22900, True),
        ("Soft Serve Cup", 9900, False),
    ):
        await _get_or_create_product(
            session,
            category=desserts,
            name=name,
            actor=actor,
            food_type="vegetarian",
            contains_dairy=True,
            contains_gluten=True,
            contains_egg=contains_egg,
            base_price_minor=price,
        )

    # --- Combos ----------------------------------------------------------
    combos = categories["combos"]
    for name, price, food_type, description in (
        (
            "Classic Veg Meal",
            29900,
            "vegetarian",
            "Includes: RKPR Classic Veg Burger, classic fries, and 300 ml cola.",
        ),
        (
            "Paneer Power Meal",
            37900,
            "vegetarian",
            "Includes: Spicy Paneer Burger, peri-peri fries, and iced tea.",
        ),
        (
            "Chicken Crunch Meal",
            42900,
            "non_vegetarian",
            "Includes: Double Crunch Chicken Burger, classic fries, and cola.",
        ),
        (
            "Pizza Sharing Combo",
            69900,
            "vegetarian",
            "Includes: One 11-inch Farmhouse Veg Pizza, garlic bread, two beverages, and one "
            "brownie.",
        ),
        (
            "Family Feast Veg",
            124900,
            "vegetarian",
            "Includes: Two 11-inch vegetarian pizzas, two veg burgers, two large fries, four "
            "beverages, and two desserts.",
        ),
        (
            "Family Feast Mixed",
            149900,
            "non_vegetarian",
            "Includes: One BBQ Chicken Pizza, one Farmhouse Pizza, two chicken burgers, two "
            "fries, four beverages, and two desserts.",
        ),
    ):
        await _get_or_create_product(
            session,
            category=combos,
            name=name,
            actor=actor,
            description=description,
            food_type=food_type,
            base_price_minor=price,
        )

    # --- Add-ons and modifiers (PROJECT_PLAN.md section 7.9) ------------
    addons_group = await session.scalar(
        select(ModifierGroup).where(ModifierGroup.name == "Add-ons")
    )
    if addons_group is None:
        addons_group = ModifierGroup(
            id=uuid.uuid4(),
            name="Add-ons",
            min_select=0,
            max_select=5,
            is_required=False,
            created_by=actor.id if actor else None,
        )
        session.add(addons_group)
        await session.flush()

        for sort_order, (name, price) in enumerate(
            (
                ("Cheese slice", 3500),
                ("Extra paneer patty", 8000),
                ("Extra chicken patty", 10000),
                ("Extra vegetable patty", 6000),
                ("Jalapeños", 2500),
                ("Extra sauce", 2000),
                ("Gluten-aware bun substitute", 6000),
                ("Make it Jain", 0),
                ("Make it extra spicy", 0),
                ("Remove ingredient", 0),
            )
        ):
            modifier = await session.scalar(select(Modifier).where(Modifier.name == name))
            if modifier is None:
                modifier = Modifier(
                    id=uuid.uuid4(),
                    name=name,
                    default_price_minor=price,
                    created_by=actor.id if actor else None,
                )
                session.add(modifier)
                await session.flush()
            session.add(
                ModifierGroupItem(
                    modifier_group_id=addons_group.id,
                    modifier_id=modifier.id,
                    sort_order=sort_order,
                    created_by=actor.id if actor else None,
                )
            )

        for sort_order, product in enumerate(burger_products):
            session.add(
                ProductModifierGroup(
                    product_id=product.id,
                    modifier_group_id=addons_group.id,
                    sort_order=sort_order,
                    created_by=actor.id if actor else None,
                )
            )
