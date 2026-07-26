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
    # Added during Phase 5 implementation — DATABASE_AND_API.md section 4.4
    # only lists the five above as representative examples ("the complete
    # registry is represented in code"); Phase 5 needs distinct, auditable
    # actions the coarse `customers.update` doesn't separately gate.
    PermissionDef("customers.archive", "Archive customer records.", is_sensitive=True),
    PermissionDef("customers.restore", "Restore archived customer records."),
    PermissionDef("customers.assign", "Assign customers to staff."),
    PermissionDef("customers.notes.manage", "Create and edit customer notes."),
    PermissionDef(
        "customers.notes.sensitive.read", "Read sensitive customer notes.", is_sensitive=True
    ),
    PermissionDef("customers.tags.manage", "Add and remove customer tags."),
    # Leads
    PermissionDef("leads.view", "View leads."),
    PermissionDef("leads.create", "Create leads."),
    PermissionDef("leads.update", "Update leads."),
    PermissionDef("leads.assign", "Assign leads to staff."),
    PermissionDef("leads.transition", "Transition lead status."),
    # Added during Phase 5 implementation, same rationale as the customers
    # group above.
    PermissionDef("leads.archive", "Archive lead records.", is_sensitive=True),
    PermissionDef("leads.restore", "Restore archived lead records."),
    PermissionDef("leads.followup.manage", "Schedule, complete, and reschedule follow-ups."),
    PermissionDef("leads.notes.manage", "Add lead activity notes."),
    PermissionDef("leads.convert", "Convert a lead into a customer.", is_sensitive=True),
    PermissionDef("leads.export", "Export lead data.", is_sensitive=True),
    # Orders. Replaces the Phase 3 placeholder set (orders.transition,
    # orders.cancel.request/.approve, orders.refund.request/.approve,
    # orders.discount.apply) — not kept as aliases, same treatment Phase 6
    # gave menu.manage. This phase's own explicit instruction names
    # orders.view/.create/.update/.cancel/.complete/.assign/
    # .payments.manage/.discount.override/.notes.manage "as examples";
    # orders.transition is kept alongside them (not one of the named
    # examples) to separately gate ordinary happy-path progression
    # (draft -> ... -> ready) from the more sensitive, individually-named
    # orders.cancel and orders.complete actions. There is no separate
    # refund permission: refunds are a payment_status value recorded
    # through orders.payments.manage, not a standalone gateway workflow —
    # this phase explicitly forbids payment gateway integration.
    PermissionDef("orders.view", "View orders."),
    PermissionDef("orders.create", "Create orders."),
    PermissionDef("orders.update", "Update order details."),
    PermissionDef("orders.transition", "Advance order status through the standard workflow."),
    PermissionDef("orders.cancel", "Cancel an order.", is_sensitive=True),
    PermissionDef("orders.complete", "Mark an order completed."),
    PermissionDef("orders.assign", "Assign staff to an order."),
    PermissionDef("orders.payments.manage", "Record and update order payments."),
    PermissionDef(
        "orders.discount.override", "Apply manual or manager-override discounts.", is_sensitive=True
    ),
    PermissionDef("orders.notes.manage", "Add and edit order notes."),
    # Menu
    PermissionDef("menu.view", "View the menu catalogue."),
    # `menu.manage` (a Phase 3 placeholder anticipating this phase) is
    # replaced, not kept as an alias, by the granular set below — this
    # phase's own explicit instruction names these exact codes, and CLAUDE.md
    # section 24 already forbids a vague `.manage` catch-all once specific
    # actions exist to gate instead. Categories, modifiers, and images each
    # get their own code since they are independently permissionable
    # sub-areas (a role might manage products but not touch images, etc.).
    PermissionDef("menu.create", "Create menu products."),
    PermissionDef("menu.update", "Update menu products and variants."),
    PermissionDef("menu.archive", "Archive menu products.", is_sensitive=True),
    PermissionDef("menu.restore", "Restore archived menu products."),
    PermissionDef("menu.categories.manage", "Create, edit, reorder, and archive categories."),
    PermissionDef(
        "menu.modifiers.manage", "Manage modifier groups, modifiers, and their mappings."
    ),
    PermissionDef("menu.images.manage", "Upload, delete, and reorder product images."),
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
