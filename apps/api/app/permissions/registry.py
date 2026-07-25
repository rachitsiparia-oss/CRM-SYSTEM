"""The single canonical capability registry.

DATABASE_AND_API.md section 4.4 and SECURITY_PERFORMANCE_AND_QUALITY.md
section 4.1 both describe this registry as "represented in code from a
single source" — this module is that source. The `permissions` table is
synchronized from `PERMISSIONS` below (see `app.db.seed`); no other module,
migration, or document may define a competing or differently-shaped list.

Code format (locked, DATABASE_AND_API.md section 4.4): lowercase,
dot-separated, domain first, action or sub-action after the domain.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PermissionDef:
    code: str
    description: str
    is_sensitive: bool = False

    @property
    def module(self) -> str:
        return self.code.split(".", 1)[0]

    @property
    def action(self) -> str:
        return self.code.split(".", 1)[1]


# Union of the representative lists in DATABASE_AND_API.md section 4.4 and
# SECURITY_PERFORMANCE_AND_QUALITY.md section 4.1 — both documents state
# they draw from the same underlying registry and neither claims to be
# exhaustive on its own. `is_sensitive` follows
# SECURITY_PERFORMANCE_AND_QUALITY.md section 4.3 (high-risk action examples).
PERMISSIONS: tuple[PermissionDef, ...] = (
    PermissionDef("dashboard.view", "View the dashboard home."),
    # Customers
    PermissionDef("customers.view", "View customer records."),
    PermissionDef("customers.create", "Create customer records."),
    PermissionDef("customers.update", "Update customer records."),
    PermissionDef("customers.merge", "Merge duplicate customer records.", is_sensitive=True),
    PermissionDef("customers.export", "Export customer data.", is_sensitive=True),
    # Leads
    PermissionDef("leads.view", "View leads."),
    PermissionDef("leads.create", "Create leads."),
    PermissionDef("leads.update", "Update leads."),
    PermissionDef("leads.assign", "Assign leads to staff."),
    PermissionDef("leads.transition", "Transition lead status."),
    # Orders
    PermissionDef("orders.view", "View orders."),
    PermissionDef("orders.create", "Create orders."),
    PermissionDef("orders.update", "Update orders."),
    PermissionDef("orders.transition", "Transition order status."),
    PermissionDef("orders.discount.apply", "Apply discounts to orders.", is_sensitive=True),
    PermissionDef("orders.cancel.request", "Request order cancellation."),
    PermissionDef("orders.cancel.approve", "Approve order cancellation.", is_sensitive=True),
    PermissionDef("orders.refund.request", "Request an order refund."),
    PermissionDef("orders.refund.approve", "Approve an order refund.", is_sensitive=True),
    # Menu
    PermissionDef("menu.view", "View the menu catalogue."),
    PermissionDef("menu.manage", "Manage the menu catalogue."),
    # Inventory
    PermissionDef("inventory.view", "View inventory."),
    PermissionDef("inventory.adjust", "Adjust inventory stock levels."),
    PermissionDef("inventory.receive", "Receive inventory from suppliers."),
    PermissionDef("inventory.transfer", "Transfer inventory between locations."),
    # Reservations
    PermissionDef("reservations.view", "View reservations."),
    PermissionDef("reservations.create", "Create reservations."),
    PermissionDef("reservations.update", "Update reservations."),
    PermissionDef("reservations.approve", "Approve reservations."),
    PermissionDef("reservations.transition", "Transition reservation status."),
    # Communications
    PermissionDef("communications.view", "View communications."),
    PermissionDef("communications.send", "Send communications."),
    # Campaigns
    PermissionDef("campaigns.view", "View marketing campaigns."),
    PermissionDef("campaigns.create", "Create marketing campaigns."),
    PermissionDef("campaigns.approve", "Approve marketing campaigns.", is_sensitive=True),
    PermissionDef("campaigns.send", "Send marketing campaigns.", is_sensitive=True),
    # Loyalty
    PermissionDef("loyalty.view", "View loyalty accounts."),
    PermissionDef("loyalty.adjust", "Adjust loyalty balances.", is_sensitive=True),
    # Feedback and complaints
    PermissionDef("feedback.view", "View customer feedback."),
    PermissionDef("complaints.manage", "Manage customer complaints."),
    # Staff, roles, and permissions
    PermissionDef("staff.view", "View staff user directory."),
    PermissionDef("staff.manage", "Manage staff user accounts.", is_sensitive=True),
    PermissionDef("staff.hr_sensitive.read", "Read HR-sensitive staff fields.", is_sensitive=True),
    PermissionDef("roles.view", "View roles and permissions."),
    PermissionDef(
        "roles.manage", "Manage role-permission and staff-role assignments.", is_sensitive=True
    ),
    # Reports
    PermissionDef("reports.view", "View reports."),
    PermissionDef("reports.export", "Export reports.", is_sensitive=True),
    # Settings
    PermissionDef("settings.view", "View system settings."),
    PermissionDef("settings.manage", "Manage system settings.", is_sensitive=True),
    PermissionDef(
        "settings.integrations.update",
        "Update integration credentials and configuration.",
        is_sensitive=True,
    ),
    # Audit and system
    PermissionDef("audit.view", "View the audit trail.", is_sensitive=True),
    PermissionDef("system.health_view", "View system health status."),
)

PERMISSION_CODES: frozenset[str] = frozenset(p.code for p in PERMISSIONS)

if len(PERMISSION_CODES) != len(PERMISSIONS):
    raise RuntimeError("Duplicate permission code detected in the canonical registry.")


def get_permission(code: str) -> PermissionDef:
    for permission in PERMISSIONS:
        if permission.code == code:
            return permission
    raise KeyError(f"Unknown permission code: {code!r}")
