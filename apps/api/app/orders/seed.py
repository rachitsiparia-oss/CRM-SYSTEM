"""Idempotent development seed data for orders — this phase's own
instruction: "realistic RKPR orders spanning all listed sources and
multiple statuses (Completed, Preparing, Cancelled, Pending), reusing
existing customers and menu."

Reuses app.orders.service directly (create_order/transition_order/
add_payment) rather than constructing rows by hand, the same precedent
app.customers.seed sets by calling app.customers.service helpers — so seed
data exercises the exact same validation, pricing, audit, and timeline
logic real API calls do. Each order uses a fixed idempotency_key so reruns
never duplicate; `order.status == "draft"` (only ever true immediately
after first creation, before any transition below) gates whether the
post-creation transition/payment steps run on a rerun.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Customer, Modifier, Order, Product, ProductVariant, StaffUser
from app.orders import service
from app.orders.schemas import (
    OrderCreateIn,
    OrderDiscountIn,
    OrderItemCreateIn,
    OrderItemModifierIn,
    OrderPaymentCreateIn,
)


async def _system_actor(session: AsyncSession) -> StaffUser | None:
    stmt = select(StaffUser).where(StaffUser.is_privileged.is_(True)).limit(1)
    result = await session.scalar(stmt)
    return result


async def _customer_id(session: AsyncSession, email: str) -> uuid.UUID | None:
    result = await session.scalar(select(Customer.id).where(Customer.primary_email == email))
    return result


async def _product_id(session: AsyncSession, name: str) -> uuid.UUID:
    product_id = await session.scalar(select(Product.id).where(Product.name == name))
    if product_id is None:
        raise RuntimeError(f"Seed menu product not found: {name!r} — run seed_menu() first.")
    return product_id


async def _variant_id(session: AsyncSession, product_id: uuid.UUID, name: str) -> uuid.UUID:
    variant_id = await session.scalar(
        select(ProductVariant.id).where(
            ProductVariant.product_id == product_id, ProductVariant.name == name
        )
    )
    if variant_id is None:
        raise RuntimeError(f"Seed menu variant not found: {name!r} for product {product_id}.")
    return variant_id


async def _modifier_id(session: AsyncSession, name: str) -> uuid.UUID | None:
    result = await session.scalar(select(Modifier.id).where(Modifier.name == name))
    return result


async def seed_orders(session: AsyncSession) -> None:
    actor = await _system_actor(session)
    if actor is None:
        return

    ananya_id = await _customer_id(session, "ananya.rao@example.test")
    rahul_id = await _customer_id(session, "rahul.mehta@example.test")
    shreya_id = await _customer_id(session, "shreya.kulkarni@example.test")
    brightwave_id = await _customer_id(session, "accounts@brightwave.example.test")
    priya_id = await _customer_id(session, "priya.sharma@example.test")
    karthik_id = await _customer_id(session, "karthik.iyer@example.test")

    classic_veg_burger = await _product_id(session, "RKPR Classic Veg Burger")
    bbq_chicken_burger = await _product_id(session, "Smoky BBQ Chicken Burger")
    jain_aloo_burger = await _product_id(session, "Jain Aloo Crunch Burger")
    double_crunch_burger = await _product_id(session, "Double Crunch Chicken Burger")
    margherita_pizza = await _product_id(session, "Margherita Pizza")
    bbq_chicken_pizza = await _product_id(session, "BBQ Chicken Pizza")
    crispy_veg_taco = await _product_id(session, "Crispy Veg Taco")
    loaded_cheese_fries = await _product_id(session, "Loaded Cheese Fries")
    onion_rings = await _product_id(session, "Onion Rings")

    margherita_11in = await _variant_id(session, margherita_pizza, "11-inch")
    bbq_chicken_pizza_8in = await _variant_id(session, bbq_chicken_pizza, "8-inch")

    cheese_slice_id = await _modifier_id(session, "Cheese slice")
    cheese_modifiers = (
        [OrderItemModifierIn(modifier_id=cheese_slice_id, quantity=1)]
        if cheese_slice_id is not None
        else []
    )

    # 1. Website delivery order for Ananya — full happy-path lifecycle,
    #    completed and paid via UPI.
    order = await service.create_order(
        session,
        actor=actor,
        payload=OrderCreateIn(
            customer_id=ananya_id,
            source="website",
            order_type="delivery",
            items=[
                OrderItemCreateIn(
                    product_id=classic_veg_burger, quantity=2, modifiers=cheese_modifiers
                )
            ],
            charges=[],
            idempotency_key="seed-order-website-ananya-1",
        ),
        request=None,
    )
    if order.status == "draft":
        for target in ("pending_confirmation", "confirmed", "preparing", "ready", "completed"):
            await service.transition_order(
                session,
                actor=actor,
                order=order,
                new_status=target,
                reason=None,
                request=None,
            )
        await service.add_payment(
            session,
            actor=actor,
            order=order,
            payload=OrderPaymentCreateIn(
                method="upi", status="paid", amount_minor=order.grand_total_minor
            ),
            request=None,
        )

    # 2. Zomato delivery order for Rahul — currently preparing, partially
    #    paid in cash.
    order = await service.create_order(
        session,
        actor=actor,
        payload=OrderCreateIn(
            customer_id=rahul_id,
            source="zomato",
            order_type="delivery",
            items=[
                OrderItemCreateIn(product_id=bbq_chicken_burger, quantity=1),
                OrderItemCreateIn(
                    product_id=margherita_pizza, variant_id=margherita_11in, quantity=1
                ),
            ],
            idempotency_key="seed-order-zomato-rahul-1",
        ),
        request=None,
    )
    if order.status == "draft":
        for target in ("pending_confirmation", "confirmed", "preparing"):
            await service.transition_order(
                session, actor=actor, order=order, new_status=target, reason=None, request=None
            )
        # The payment record itself is "paid" (this specific cash amount was
        # actually received); the order's derived payment_status becomes
        # "partial" once _recompute_payment_status compares it to
        # grand_total_minor — a payment record's own status describes
        # whether that transaction succeeded, not the order's overall
        # payment coverage.
        await service.add_payment(
            session,
            actor=actor,
            order=order,
            payload=OrderPaymentCreateIn(
                method="cash", status="paid", amount_minor=order.grand_total_minor // 2
            ),
            request=None,
        )

    # 3. Walk-in dine-in order, no customer on file — awaiting confirmation.
    order = await service.create_order(
        session,
        actor=actor,
        payload=OrderCreateIn(
            source="walk_in",
            order_type="dine_in",
            items=[OrderItemCreateIn(product_id=crispy_veg_taco, quantity=3)],
            idempotency_key="seed-order-walkin-1",
        ),
        request=None,
    )
    if order.status == "draft":
        await service.transition_order(
            session,
            actor=actor,
            order=order,
            new_status="pending_confirmation",
            reason=None,
            request=None,
        )

    # 4. Phone-call takeaway order for Shreya — cancelled before confirmation.
    order = await service.create_order(
        session,
        actor=actor,
        payload=OrderCreateIn(
            customer_id=shreya_id,
            source="phone_call",
            order_type="takeaway",
            items=[OrderItemCreateIn(product_id=jain_aloo_burger, quantity=1)],
            idempotency_key="seed-order-phone-shreya-1",
        ),
        request=None,
    )
    if order.status == "draft":
        await service.transition_order(
            session,
            actor=actor,
            order=order,
            new_status="pending_confirmation",
            reason=None,
            request=None,
        )
        await service.transition_order(
            session,
            actor=actor,
            order=order,
            new_status="cancelled",
            reason="Customer called back to cancel before confirmation.",
            request=None,
        )

    # 5. Swiggy delivery order for BrightWave Technologies — ready for
    #    pickup by the delivery partner, payment still pending.
    order = await service.create_order(
        session,
        actor=actor,
        payload=OrderCreateIn(
            customer_id=brightwave_id,
            source="swiggy",
            order_type="delivery",
            items=[
                OrderItemCreateIn(
                    product_id=bbq_chicken_pizza, variant_id=bbq_chicken_pizza_8in, quantity=3
                )
            ],
            idempotency_key="seed-order-swiggy-brightwave-1",
        ),
        request=None,
    )
    if order.status == "draft":
        for target in ("pending_confirmation", "confirmed", "preparing", "ready"):
            await service.transition_order(
                session, actor=actor, order=order, new_status=target, reason=None, request=None
            )

    # 6. POS dine-in order for Priya — confirmed, kitchen not yet started.
    order = await service.create_order(
        session,
        actor=actor,
        payload=OrderCreateIn(
            customer_id=priya_id,
            source="pos",
            order_type="dine_in",
            items=[
                OrderItemCreateIn(product_id=margherita_pizza, quantity=1),
                OrderItemCreateIn(product_id=loaded_cheese_fries, quantity=1),
            ],
            idempotency_key="seed-order-pos-priya-1",
        ),
        request=None,
    )
    if order.status == "draft":
        for target in ("pending_confirmation", "confirmed"):
            await service.transition_order(
                session, actor=actor, order=order, new_status=target, reason=None, request=None
            )

    # 7. Manual takeaway order for Karthik — left in draft (staff still
    #    building it).
    await service.create_order(
        session,
        actor=actor,
        payload=OrderCreateIn(
            customer_id=karthik_id,
            source="manual",
            order_type="takeaway",
            items=[OrderItemCreateIn(product_id=onion_rings, quantity=2)],
            idempotency_key="seed-order-manual-karthik-1",
        ),
        request=None,
    )

    # 8. WhatsApp delivery order for Rahul — preparing, with a manager-
    #    approved flat discount applied.
    order = await service.create_order(
        session,
        actor=actor,
        payload=OrderCreateIn(
            customer_id=rahul_id,
            source="whatsapp",
            order_type="delivery",
            items=[OrderItemCreateIn(product_id=double_crunch_burger, quantity=1)],
            discounts=[
                OrderDiscountIn(
                    discount_type="manager_override",
                    amount_minor=3000,
                    reason="Repeat-customer goodwill discount.",
                    approved_by=actor.id,
                )
            ],
            idempotency_key="seed-order-whatsapp-rahul-1",
        ),
        request=None,
    )
    if order.status == "draft":
        for target in ("pending_confirmation", "confirmed", "preparing"):
            await service.transition_order(
                session, actor=actor, order=order, new_status=target, reason=None, request=None
            )

    # 9. Two weeks of backdated completed orders — Phase 17.5's home
    # dashboard trend chart and top-menu-items ranking need real historical
    # spread to render meaningfully; orders 1-8 above are all created "now"
    # (TimestampMixin's server_default), which alone would show one busy
    # day and thirteen empty ones. Real business logic still creates and
    # prices each order (service.create_order/transition_order, same as
    # every order above) — only `created_at` is backdated afterward via a
    # direct UPDATE, since the order pipeline has no "as of" parameter and
    # backdating is a seed-only concern, not a real feature. Deterministic
    # per day (not random) so reruns stay idempotent, matching this
    # function's existing idempotency_key convention.
    trend_customers = [ananya_id, rahul_id, shreya_id, priya_id, karthik_id, brightwave_id]
    trend_products = [
        (classic_veg_burger, 2),
        (bbq_chicken_burger, 1),
        (margherita_pizza, 1),
        (crispy_veg_taco, 3),
        (loaded_cheese_fries, 2),
        (double_crunch_burger, 1),
        (onion_rings, 2),
    ]
    for day_offset in range(1, 14):
        product_id, quantity = trend_products[day_offset % len(trend_products)]
        customer_id = trend_customers[day_offset % len(trend_customers)]
        order = await service.create_order(
            session,
            actor=actor,
            payload=OrderCreateIn(
                customer_id=customer_id,
                source="website",
                order_type="takeaway",
                items=[OrderItemCreateIn(product_id=product_id, quantity=quantity)],
                idempotency_key=f"seed-order-trend-day-{day_offset}",
            ),
            request=None,
        )
        if order.status == "draft":
            for target in ("pending_confirmation", "confirmed", "preparing", "ready", "completed"):
                await service.transition_order(
                    session, actor=actor, order=order, new_status=target, reason=None, request=None
                )
            await service.add_payment(
                session,
                actor=actor,
                order=order,
                payload=OrderPaymentCreateIn(
                    method="upi", status="paid", amount_minor=order.grand_total_minor
                ),
                request=None,
            )
        backdated_at = datetime.now(UTC) - timedelta(days=day_offset)
        await session.execute(
            update(Order).where(Order.id == order.id).values(created_at=backdated_at)
        )

    await session.flush()
