import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OrderSource = Literal[
    "pos", "walk_in", "website", "whatsapp", "phone_call", "zomato", "swiggy", "manual"
]
OrderType = Literal["dine_in", "takeaway", "delivery"]
OrderStatus = Literal[
    "draft", "pending_confirmation", "confirmed", "preparing", "ready", "completed", "cancelled"
]
PaymentStatus = Literal["pending", "partial", "paid", "refunded", "failed"]
PaymentMethod = Literal["cash", "card", "upi", "online"]
OrderDiscountType = Literal[
    "flat", "percentage", "manual", "coupon_placeholder", "manager_override"
]
OrderChargeType = Literal["packaging", "delivery", "service", "other"]


class OrderItemModifierIn(BaseModel):
    modifier_id: uuid.UUID
    quantity: int = Field(default=1, ge=1)


class OrderItemCreateIn(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = Field(default=1, ge=1)
    modifiers: list[OrderItemModifierIn] = Field(default_factory=list)
    kitchen_note: str | None = Field(default=None, max_length=500)


class OrderDiscountIn(BaseModel):
    discount_type: OrderDiscountType
    amount_minor: int | None = Field(default=None, ge=0)
    percentage: float | None = Field(default=None, ge=0, le=100)
    reason: str = Field(min_length=1, max_length=500)
    approved_by: uuid.UUID


class OrderTaxIn(BaseModel):
    tax_name: str = Field(min_length=1, max_length=64)
    rate_percentage: float | None = Field(default=None, ge=0, le=100)
    amount_minor: int | None = Field(default=None, ge=0)


class OrderChargeIn(BaseModel):
    charge_type: OrderChargeType
    amount_minor: int = Field(ge=0)


class OrderCreateIn(BaseModel):
    customer_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    source: OrderSource
    order_type: OrderType
    assigned_staff_id: uuid.UUID | None = None
    items: list[OrderItemCreateIn] = Field(min_length=1)
    discounts: list[OrderDiscountIn] = Field(default_factory=list)
    taxes: list[OrderTaxIn] = Field(default_factory=list)
    charges: list[OrderChargeIn] = Field(default_factory=list)
    internal_notes: str | None = None
    customer_notes: str | None = None
    estimated_completion_time: datetime | None = None
    idempotency_key: str = Field(min_length=1, max_length=160)


class OrderUpdateIn(BaseModel):
    customer_id: uuid.UUID | None = None
    lead_id: uuid.UUID | None = None
    internal_notes: str | None = None
    customer_notes: str | None = None
    estimated_completion_time: datetime | None = None
    expected_version: int | None = None


class OrderTransitionIn(BaseModel):
    new_status: OrderStatus
    reason: str | None = Field(default=None, max_length=500)


class OrderAssignIn(BaseModel):
    assigned_staff_id: uuid.UUID


class OrderPaymentCreateIn(BaseModel):
    method: PaymentMethod
    status: PaymentStatus = "paid"
    amount_minor: int = Field(ge=0)
    reference: str | None = Field(default=None, max_length=200)
    notes: str | None = None


class OrderPaymentUpdateIn(BaseModel):
    status: PaymentStatus


class OrderNoteIn(BaseModel):
    content: str = Field(min_length=1)
    is_internal: bool = True


class OrderItemModifierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    modifier_id: uuid.UUID | None
    modifier_name_snapshot: str
    price_minor_snapshot: int
    quantity: int


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID | None
    variant_id: uuid.UUID | None
    product_name_snapshot: str
    variant_name_snapshot: str | None
    product_code_snapshot: str | None
    quantity: int
    unit_price_minor: int
    discount_minor: int
    tax_minor: int
    final_price_minor: int
    kitchen_note: str | None
    status: str
    modifiers: list[OrderItemModifierOut] = Field(default_factory=list)


class OrderDiscountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    discount_type: str
    amount_minor: int
    percentage: float | None
    reason: str
    approved_by: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime


class OrderTaxOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tax_name: str
    rate_percentage: float | None
    amount_minor: int
    created_at: datetime


class OrderChargeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    charge_type: str
    amount_minor: int
    created_at: datetime


class OrderPaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    method: str
    status: str
    amount_minor: int
    reference: str | None
    notes: str | None
    recorded_by: uuid.UUID
    recorded_at: datetime
    updated_at: datetime | None
    updated_by: uuid.UUID | None


class OrderNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    content: str
    is_internal: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime | None
    updated_by: uuid.UUID | None


class OrderTimelineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    event_type: str
    summary: str
    event_metadata: dict[str, object] | None = None
    performed_by: uuid.UUID | None
    occurred_at: datetime


class OrderStatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    previous_status: str | None
    new_status: str
    actor_id: uuid.UUID | None
    reason: str | None
    created_at: datetime


class OrderAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    staff_id: uuid.UUID
    assigned_by: uuid.UUID | None
    assigned_at: datetime
    unassigned_at: datetime | None


class OrderListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID | None
    source: str
    order_type: str
    status: str
    payment_status: str
    assigned_staff_id: uuid.UUID | None
    grand_total_minor: int
    estimated_completion_time: datetime | None
    created_at: datetime


class OrderStatusCountsOut(BaseModel):
    pending_confirmation: int
    preparing: int
    ready: int
    completed: int
    cancelled: int


class RecentOrderActivityOut(BaseModel):
    order_id: uuid.UUID
    order_number: str
    event_type: str
    summary: str
    occurred_at: datetime


class OrderDashboardStatsOut(BaseModel):
    today_order_count: int
    status_counts_today: OrderStatusCountsOut
    revenue_today_minor: int
    average_order_value_minor: int
    recent_activity: list[RecentOrderActivityOut]


class TopMenuItemOut(BaseModel):
    """Ranked by revenue within the window — grouped by
    `product_name_snapshot` (not a live product join) so a later menu
    rename/deletion never changes what a historical ranking shows."""

    product_name: str
    quantity_sold: int
    revenue_minor: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    customer_id: uuid.UUID | None
    lead_id: uuid.UUID | None
    source: str
    order_type: str
    status: str
    payment_status: str
    assigned_staff_id: uuid.UUID | None
    subtotal_minor: int
    discount_minor: int
    tax_minor: int
    charges_minor: int
    grand_total_minor: int
    internal_notes: str | None
    customer_notes: str | None
    estimated_completion_time: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = Field(default_factory=list)
    discounts: list[OrderDiscountOut] = Field(default_factory=list)
    taxes: list[OrderTaxOut] = Field(default_factory=list)
    charges: list[OrderChargeOut] = Field(default_factory=list)
