"""Default role -> permission-code grants, seeded once per role at
migration/seed time and editable afterward through `roles.manage`
(`role_permissions` is the live source once seeded; this module is only the
initial matrix, not a second permission registry — every code referenced
here must already exist in `app.permissions.registry`).

DATABASE_AND_API.md and SECURITY_PERFORMANCE_AND_QUALITY.md define the
permission codes and the 15 system roles, but neither document specifies
which role gets which permission — that mapping is a Phase 3 implementation
decision, made here.
"""

from app.permissions.registry import PERMISSION_CODES

_ALL_VIEW = tuple(code for code in PERMISSION_CODES if code.endswith(".view"))

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "owner": tuple(sorted(PERMISSION_CODES)),
    "general_manager": tuple(sorted(PERMISSION_CODES - {"settings.integrations.update"})),
    "operations_manager": (
        "dashboard.view",
        "customers.view",
        "customers.create",
        "customers.update",
        "customers.archive",
        "customers.restore",
        "customers.assign",
        "customers.notes.manage",
        "customers.tags.manage",
        "customers.merge",
        "leads.view",
        "leads.create",
        "leads.update",
        "leads.assign",
        "leads.transition",
        "leads.archive",
        "leads.restore",
        "leads.followup.manage",
        "leads.notes.manage",
        "leads.convert",
        "leads.export",
        "orders.view",
        "orders.create",
        "orders.update",
        "orders.transition",
        "orders.cancel",
        "orders.complete",
        "orders.assign",
        "orders.payments.manage",
        "orders.notes.manage",
        "menu.view",
        # Operations manager oversees stock but is not the store keeper:
        # full visibility (including cost, since they own operational
        # spend) plus approval authority, without the day-to-day
        # receipt/transfer/count data entry that inventory_manager does.
        "inventory.view",
        "inventory.cost.view",
        "inventory.recipes.view",
        "inventory.adjustments.approve",
        "inventory.wastage.approve",
        "inventory.counts.approve",
        # Same approval-authority pattern as the inventory grants above:
        # operations manager approves/cancels/completes reservations and
        # oversees the floor, but reservation-policy configuration
        # (business hours, holidays, deposit/notice rules) stays with
        # owner/general_manager, the same restriction already applied to
        # `settings.manage`.
        "reservations.view",
        "reservations.create",
        "reservations.update",
        "reservations.approve",
        "reservations.transition",
        "reservations.cancel",
        "reservations.complete",
        "reservations.assign",
        "reservations.notes.manage",
        "reservations.tags.manage",
        "reservations.waitlist.manage",
        "reservations.tables.manage",
        "communications.view",
        "communications.send",
        "staff.view",
        "reports.view",
        "reports.export",
    ),
    "finance_manager": (
        "dashboard.view",
        "orders.view",
        "orders.payments.manage",
        "orders.discount.override",
        # Finance owns valuation and cost reporting, and signs off on
        # adjustments that move stock value — but never records stock
        # movements itself (no receipts/transfers/wastage/counts).
        "inventory.view",
        "inventory.cost.view",
        "inventory.adjustments.approve",
        "loyalty.view",
        "loyalty.adjust",
        "reports.view",
        "reports.export",
        "settings.view",
        "audit.view",
    ),
    "kitchen_manager": (
        "dashboard.view",
        "menu.view",
        "menu.create",
        "menu.update",
        "menu.archive",
        "menu.restore",
        "menu.categories.manage",
        "menu.modifiers.manage",
        "menu.images.manage",
        # Kitchen manager owns recipes (they define what a dish consumes)
        # and records kitchen-floor stock reality — wastage, counts,
        # receipts into the kitchen — but does not approve their own
        # wastage or adjustments, and has no supplier/unit/location
        # administration.
        "inventory.view",
        "inventory.cost.view",
        "inventory.recipes.view",
        "inventory.recipes.manage",
        "inventory.receipts.create",
        "inventory.receipts.post",
        "inventory.wastage.create",
        "inventory.transfers.create",
        "inventory.transfers.post",
        "inventory.counts.create",
        "inventory.counts.submit",
        "orders.view",
        "orders.transition",
        "staff.view",
    ),
    "inventory_manager": (
        "dashboard.view",
        # The store keeper: full day-to-day stock operations and master
        # data, and the approver for counts and wastage. Deliberately NOT
        # granted inventory.adjustments.approve (a manual quantity
        # correction is signed off by operations/finance, not by the
        # person who recorded it) or inventory.balances.rebuild (a
        # last-resort maintenance action reserved for owner/GM).
        "inventory.view",
        "inventory.cost.view",
        "inventory.items.create",
        "inventory.items.update",
        "inventory.items.archive",
        "inventory.items.restore",
        "inventory.suppliers.manage",
        "inventory.units.manage",
        "inventory.locations.manage",
        "inventory.categories.manage",
        "inventory.recipes.view",
        "inventory.receipts.create",
        "inventory.receipts.post",
        "inventory.receipts.reverse",
        "inventory.adjustments.create",
        "inventory.wastage.create",
        "inventory.wastage.approve",
        "inventory.transfers.create",
        "inventory.transfers.post",
        "inventory.transfers.reverse",
        "inventory.counts.create",
        "inventory.counts.submit",
        "inventory.counts.approve",
        "orders.view",
        "staff.view",
        "reports.view",
    ),
    "reservation_manager": (
        "dashboard.view",
        # The dedicated domain owner: full reservation lifecycle authority,
        # including the one config surface operations_manager is
        # deliberately withheld from (`.settings.manage` — business hours,
        # holidays, deposit/notice policy).
        "reservations.view",
        "reservations.create",
        "reservations.update",
        "reservations.approve",
        "reservations.transition",
        "reservations.cancel",
        "reservations.complete",
        "reservations.assign",
        "reservations.notes.manage",
        "reservations.tags.manage",
        "reservations.waitlist.manage",
        "reservations.tables.manage",
        "reservations.settings.manage",
        "customers.view",
        "communications.view",
        "communications.send",
        "staff.view",
    ),
    "customer_support_agent": (
        "dashboard.view",
        "customers.view",
        "customers.update",
        "customers.notes.manage",
        "customers.tags.manage",
        "leads.view",
        "leads.update",
        "leads.notes.manage",
        "leads.followup.manage",
        "leads.convert",
        "orders.view",
        "reservations.view",
        "communications.view",
        "communications.send",
        "feedback.view",
        "complaints.manage",
    ),
    "marketing_manager": (
        "dashboard.view",
        "campaigns.view",
        "campaigns.create",
        "campaigns.approve",
        "campaigns.send",
        "customers.view",
        "customers.tags.manage",
        "leads.view",
        "leads.notes.manage",
        "leads.export",
        "loyalty.view",
        "reports.view",
        "communications.view",
        "communications.send",
    ),
    "hr_manager": (
        "dashboard.view",
        "staff.view",
        "staff.manage",
        "staff.hr_sensitive.read",
        "roles.view",
        "roles.manage",
        "audit.view",
    ),
    "shift_supervisor": (
        "dashboard.view",
        "orders.view",
        "orders.update",
        "orders.transition",
        "orders.cancel",
        "orders.complete",
        "orders.assign",
        "staff.view",
        # On-shift floor authority: seat guests, run the waitlist, and
        # adjust table state in real time — the same reach they already
        # have over orders — but not approve advance-booking requests or
        # touch policy/hours configuration, both reserved for
        # reservation_manager/operations_manager.
        "reservations.view",
        "reservations.create",
        "reservations.update",
        "reservations.transition",
        "reservations.cancel",
        "reservations.complete",
        "reservations.assign",
        "reservations.waitlist.manage",
        "reservations.tables.manage",
        # A supervisor on shift needs to see stock and record what the
        # floor consumed or wasted, but not approve it, not touch master
        # data, and not see supplier costs.
        "inventory.view",
        "inventory.wastage.create",
        "inventory.counts.create",
        "inventory.counts.submit",
    ),
    "kitchen_staff": (
        "dashboard.view",
        "orders.view",
        "orders.transition",
        "menu.view",
        # Quantities and recipes only — no costs, no approvals, no master
        # data. Recording wastage is the one stock write a line cook needs.
        "inventory.view",
        "inventory.recipes.view",
        "inventory.wastage.create",
    ),
    "front_of_house_staff": (
        "dashboard.view",
        "orders.view",
        "orders.create",
        "orders.update",
        "orders.transition",
        "orders.complete",
        "orders.notes.manage",
        # Front-of-house seats guests and takes walk-ins directly — the
        # same create/update/transition/complete reach they have over
        # orders — but cannot cancel a reservation or approve an advance
        # booking, both held back for a supervisor or above.
        "reservations.view",
        "reservations.create",
        "reservations.update",
        "reservations.transition",
        "reservations.complete",
        "reservations.assign",
        "reservations.waitlist.manage",
        "reservations.notes.manage",
        "customers.view",
    ),
    "delivery_coordinator": (
        "dashboard.view",
        "orders.view",
        "orders.transition",
        "orders.complete",
        "communications.view",
    ),
    "read_only_auditor": tuple(sorted({*_ALL_VIEW, "audit.view"})),
}

_unknown_codes = {
    code for codes in ROLE_PERMISSIONS.values() for code in codes if code not in PERMISSION_CODES
}
if _unknown_codes:
    raise RuntimeError(f"role_matrix references unknown permission codes: {_unknown_codes!r}")
