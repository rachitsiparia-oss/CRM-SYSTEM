"""Coupon normalization and lookup — GROWTH_AND_INTELLIGENCE.md section
6.5/6.10 ("coupon entered with different casing"). `normalize_code` is the
single point every write and read path passes a coupon code through,
matching Phase 5's phone/email normalization pattern.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime

from app.db.models import Coupon, Offer, StaffUser
from app.offers.errors import DuplicateCouponCodeError
from app.offers.schemas import CouponCreateIn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_WHITESPACE_RE = re.compile(r"\s+")


def normalize_code(raw: str) -> str:
    return _WHITESPACE_RE.sub("", raw).strip().upper()


async def get_coupon_by_code(session: AsyncSession, code: str) -> Coupon | None:
    result: Coupon | None = await session.scalar(
        select(Coupon).where(Coupon.code == normalize_code(code))
    )
    return result


async def create_coupon(
    session: AsyncSession, *, offer: Offer, payload: CouponCreateIn, actor: StaffUser
) -> Coupon:
    code = normalize_code(payload.code)
    existing = await get_coupon_by_code(session, code)
    if existing is not None:
        raise DuplicateCouponCodeError(f"Coupon code {code!r} is already in use.")

    coupon = Coupon(
        id=uuid.uuid4(),
        code=code,
        offer_id=offer.id,
        is_reusable=payload.is_reusable,
        customer_id=payload.customer_id,
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
        redemption_limit=payload.redemption_limit,
        redemption_count=0,
        generation_batch=payload.generation_batch,
        is_active=True,
    )
    session.add(coupon)
    await session.flush()
    return coupon


def is_coupon_usable(
    coupon: Coupon, *, customer_id: uuid.UUID, now: datetime | None = None
) -> str | None:
    """Returns None when usable, or a reason code string when not."""
    now = now or datetime.now(UTC)
    if not coupon.is_active:
        return "coupon_inactive"
    if coupon.starts_at is not None and now < coupon.starts_at:
        return "coupon_not_yet_active"
    if coupon.expires_at is not None and now > coupon.expires_at:
        return "coupon_expired"
    if coupon.customer_id is not None and coupon.customer_id != customer_id:
        return "coupon_not_assigned_to_customer"
    if coupon.redemption_limit is not None and coupon.redemption_count >= coupon.redemption_limit:
        return "coupon_redemption_limit_reached"
    if not coupon.is_reusable and coupon.redemption_count >= 1:
        return "coupon_already_used"
    return None
