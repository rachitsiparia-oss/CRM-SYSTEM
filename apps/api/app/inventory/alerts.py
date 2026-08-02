"""Low-stock alert dispatch — INTEGRATIONS_AUTOMATIONS_REALTIME.md section
14.4 ("Stock below reorder threshold creates low-stock alert. Stock below
critical threshold creates urgent alert."). `InventoryItem.stock_status`
is already derived synchronously on every ledger-affecting operation
(`app.inventory.ledger.derive_stock_status`/`refresh_item_rollup`), so the
*data* has always been current — nothing ever pushed a notification when
an item crossed into `low_stock`/`critical_stock`/`out_of_stock` before
this phase (confirmed: zero `notify()` calls anywhere in `app.inventory`
previously). Fans out to `inventory_manager`/`owner`/`general_manager`,
the same per-recipient `notify()` fan-out `app.complaints.service` already
established for role-addressed (not single-owner) alerts.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InventoryItem, Role, StaffRole, StaffUser
from app.notifications.service import notify

_ALERT_ROLES = ("inventory_manager", "owner", "general_manager")
_ALERT_STATUSES = {
    "low_stock": ("normal", "Stock is running low"),
    "critical_stock": ("high", "Stock is critically low"),
    "out_of_stock": ("urgent", "Item is out of stock"),
}


async def dispatch_low_stock_alerts(session: AsyncSession) -> int:
    items = (
        await session.scalars(
            select(InventoryItem).where(
                InventoryItem.deleted_at.is_(None),
                InventoryItem.is_active.is_(True),
                InventoryItem.stock_status.in_(_ALERT_STATUSES.keys()),
            )
        )
    ).all()
    if not items:
        return 0

    recipients = (
        await session.scalars(
            select(StaffUser.id)
            .join(StaffRole, StaffRole.staff_user_id == StaffUser.id)
            .join(Role, Role.id == StaffRole.role_id)
            .where(
                Role.code.in_(_ALERT_ROLES),
                StaffUser.account_status == "active",
                StaffUser.deleted_at.is_(None),
            )
            .distinct()
        )
    ).all()
    if not recipients:
        return 0

    dispatched = 0
    for item in items:
        priority, headline = _ALERT_STATUSES[item.stock_status]
        for recipient_id in recipients:
            result = await notify(
                session,
                notification_type="inventory.stock_alert",
                title=f"{headline}: {item.name}",
                recipient_staff_id=recipient_id,
                body=f"Current stock: {item.current_stock}.",
                priority=priority,
                record_type="inventory_item",
                record_id=item.id,
                dedup_key=f"inventory-alert:{item.id}:{item.stock_status}:{recipient_id}",
            )
            if result is not None:
                dispatched += 1
    return dispatched
