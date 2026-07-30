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
    # Inventory. Replaces the Phase 3 placeholder set (inventory.adjust,
    # inventory.receive, inventory.transfer) with the granular codes this
    # phase's own instruction names — not kept as aliases, the same
    # treatment Phase 6 gave menu.manage and Phase 7 gave the order
    # placeholders. DATABASE_AND_API.md section 25.2 and
    # CORE_CRM_MODULES.md section 8.19 both reference the old three as
    # "and related" examples drawn from the registry, never as an
    # exhaustive list, so replacing them narrows nothing that was
    # documented as complete.
    #
    # The split is deliberate along the lines that matter operationally:
    # *doing* a stock operation and *approving* it are separate grants
    # (so a store hand can record waste but not sign it off), and reading
    # costs is separate from reading stock levels (a kitchen hand needs
    # quantities, not supplier pricing).
    PermissionDef("inventory.view", "View inventory items, balances, and movements."),
    PermissionDef("inventory.items.create", "Create inventory items."),
    PermissionDef("inventory.items.update", "Update inventory items."),
    PermissionDef("inventory.items.archive", "Archive inventory items.", is_sensitive=True),
    PermissionDef("inventory.items.restore", "Restore archived inventory items."),
    PermissionDef("inventory.suppliers.manage", "Create, edit, and archive suppliers."),
    PermissionDef("inventory.units.manage", "Manage units of measure and conversions."),
    PermissionDef("inventory.locations.manage", "Manage storage locations and their stock policy."),
    PermissionDef("inventory.categories.manage", "Manage inventory categories."),
    PermissionDef("inventory.recipes.view", "View recipes and their ingredients."),
    PermissionDef("inventory.recipes.manage", "Create and edit recipes.", is_sensitive=True),
    PermissionDef("inventory.receipts.create", "Create and edit draft goods receipts."),
    PermissionDef("inventory.receipts.post", "Post a goods receipt into stock.", is_sensitive=True),
    PermissionDef(
        "inventory.receipts.reverse", "Reverse a posted goods receipt.", is_sensitive=True
    ),
    PermissionDef("inventory.adjustments.create", "Record a stock adjustment.", is_sensitive=True),
    PermissionDef(
        "inventory.adjustments.approve", "Approve a stock adjustment.", is_sensitive=True
    ),
    PermissionDef("inventory.wastage.create", "Record wastage."),
    PermissionDef("inventory.wastage.approve", "Approve recorded wastage.", is_sensitive=True),
    PermissionDef("inventory.transfers.create", "Create and edit draft stock transfers."),
    PermissionDef("inventory.transfers.post", "Post a stock transfer."),
    PermissionDef(
        "inventory.transfers.reverse", "Reverse a posted stock transfer.", is_sensitive=True
    ),
    PermissionDef("inventory.counts.create", "Create and conduct stock counts."),
    PermissionDef("inventory.counts.submit", "Submit a completed stock count for approval."),
    PermissionDef(
        "inventory.counts.approve",
        "Approve a stock count and post its variance corrections.",
        is_sensitive=True,
    ),
    PermissionDef(
        "inventory.balances.rebuild",
        "Rebuild the stock balance projection from the ledger.",
        is_sensitive=True,
    ),
    PermissionDef("inventory.cost.view", "View inventory costs, valuation, and recipe costing."),
    # Reservations. Replaces the Phase 3 placeholder set (reservations.view/
    # .create/.update/.approve/.transition) with the granular codes this
    # phase's own instruction names as examples
    # (.view/.create/.update/.cancel/.complete/.assign/.waitlist/.tables/
    # .settings) — not kept as aliases, the same treatment Phase 6, 7, and 8
    # gave their own Phase 3 placeholders. `.approve` covers both approving
    # and rejecting a pending request — PROJECT_PLAN.md section 11.2's "No
    # automated approval is permitted" makes this the one mandatory
    # human-in-the-loop gate every non-walk-in reservation must pass
    # through, so it is marked sensitive like `orders.cancel`. `.transition`
    # covers ordinary lifecycle progression (confirmed, arrived, seated,
    # no_show) the same way `orders.transition` covers an order's happy
    # path, separately from the individually-named `.cancel`/`.complete`.
    # `.tables` covers dining-area and floor/table management (mirrors
    # `inventory.locations.manage`); `.settings` covers business hours,
    # holidays, and policy configuration (mirrors `settings.manage`).
    PermissionDef("reservations.view", "View reservations."),
    PermissionDef("reservations.create", "Create reservations."),
    PermissionDef("reservations.update", "Update reservation details."),
    PermissionDef(
        "reservations.approve",
        "Approve or reject a pending reservation request.",
        is_sensitive=True,
    ),
    PermissionDef(
        "reservations.transition", "Advance reservation status through the standard workflow."
    ),
    PermissionDef("reservations.cancel", "Cancel a reservation.", is_sensitive=True),
    PermissionDef("reservations.complete", "Mark a reservation completed."),
    PermissionDef("reservations.assign", "Assign staff or tables to a reservation."),
    PermissionDef("reservations.notes.manage", "Add and edit reservation notes."),
    PermissionDef("reservations.tags.manage", "Add and remove reservation tags."),
    PermissionDef("reservations.waitlist.manage", "Manage the reservation waitlist."),
    PermissionDef("reservations.tables.manage", "Manage dining areas, tables, and table blocks."),
    PermissionDef(
        "reservations.settings.manage",
        "Manage business hours, holidays, and reservation policies.",
        is_sensitive=True,
    ),
    # Communications. Replaces the Phase 3 placeholder pair (communications.
    # view/.send) with the granular set this phase's own instruction names
    # as suggested codes — not kept as aliases, the same treatment every
    # prior phase gave its own Phase 3 placeholders. `.reply` is the
    # customer-facing send (mirrors `.create` on other domains being the
    # "do the main thing" action); `.notes.create` is the internal-note
    # equivalent, never provider-sent. `.webhooks.manage` covers viewing/
    # reprocessing the raw inbound/status webhook ledger for
    # troubleshooting — distinct from `.channels.manage` (provider/channel
    # configuration itself).
    PermissionDef("communications.view", "View conversations and messages."),
    PermissionDef("communications.create", "Start a new conversation."),
    PermissionDef("communications.reply", "Send an outbound reply in a conversation."),
    PermissionDef("communications.assign", "Assign conversations to staff."),
    PermissionDef("communications.resolve", "Resolve a conversation."),
    PermissionDef("communications.reopen", "Reopen a resolved or closed conversation."),
    PermissionDef("communications.snooze", "Snooze a conversation."),
    PermissionDef("communications.priority.manage", "Change a conversation's priority."),
    PermissionDef("communications.notes.create", "Add internal notes to a conversation."),
    PermissionDef("communications.templates.view", "View message templates."),
    PermissionDef("communications.templates.manage", "Create and edit message templates."),
    PermissionDef("communications.channels.view", "View communication channel configuration."),
    PermissionDef(
        "communications.channels.manage",
        "Manage communication channel configuration.",
        is_sensitive=True,
    ),
    PermissionDef("communications.preferences.view", "View customer communication preferences."),
    PermissionDef(
        "communications.preferences.manage", "Manage customer communication preferences."
    ),
    PermissionDef("communications.suppressions.view", "View the suppression list."),
    PermissionDef(
        "communications.suppressions.manage", "Manage the suppression list.", is_sensitive=True
    ),
    PermissionDef("communications.analytics.view", "View communication analytics."),
    PermissionDef(
        "communications.webhooks.manage",
        "View and reprocess raw provider webhook events.",
        is_sensitive=True,
    ),
    PermissionDef(
        "communications.messages.redact", "Redact a message's content.", is_sensitive=True
    ),
    PermissionDef("communications.call_logs.create", "Log a manual phone call."),
    PermissionDef("communications.call_logs.view", "View manual call logs."),
    # Operational tasks — new in Phase 10 (PROJECT_PLAN.md's Phase 10 scope
    # bullet "Operational tasks: creation sources, assignment, priority, due
    # time, completion evidence, recurring tasks"). `.view` is scoped to a
    # staff member's own assigned/created tasks; `.view_all` is the
    # team-wide view (mirrors the `orders`/`reservations` "doing vs.
    # overseeing" split).
    PermissionDef("tasks.view", "View own and assigned tasks."),
    PermissionDef("tasks.view_all", "View all staff and team tasks."),
    PermissionDef("tasks.create", "Create tasks."),
    PermissionDef("tasks.update", "Update task details."),
    PermissionDef("tasks.assign", "Assign tasks to staff or a department."),
    PermissionDef("tasks.complete", "Mark a task completed."),
    PermissionDef("tasks.reopen", "Reopen a completed or cancelled task."),
    PermissionDef("tasks.delete", "Cancel a task.", is_sensitive=True),
    # Notifications — new in Phase 10. Viewing one's own notifications
    # requires no separate grant (same "own record" principle as a staff
    # member's own profile); `.manage` is only for staff-initiated broadcast
    # notifications, not for reading one's own inbox.
    PermissionDef("notifications.manage", "Create broadcast staff notifications."),
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
