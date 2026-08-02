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
    # Knowledge Base — new in Phase 11. DATABASE_AND_API.md section 13/28
    # sketches a much lighter folders/documents model than this phase's own
    # instruction's article-lifecycle elaboration; these codes follow the
    # granular-over-catch-all convention every prior phase's Phase 3
    # placeholder replacement established. `.review`/`.approve`/`.publish`
    # are separately gated (not folded into `.update`) so an author cannot
    # self-approve when policy requires a different reviewer — enforced in
    # `app.knowledge.articles`, not just by withholding the grant.
    PermissionDef("knowledge.view", "View knowledge base articles."),
    PermissionDef("knowledge.create", "Create knowledge base articles."),
    PermissionDef("knowledge.update", "Edit knowledge base article drafts."),
    PermissionDef("knowledge.review", "Submit and comment on articles under review."),
    PermissionDef(
        "knowledge.approve", "Approve or request changes on a submitted article.", is_sensitive=True
    ),
    PermissionDef("knowledge.publish", "Publish, unpublish, and supersede article versions."),
    PermissionDef("knowledge.archive", "Archive knowledge base articles."),
    PermissionDef("knowledge.categories.manage", "Create, edit, and reorder knowledge categories."),
    PermissionDef("knowledge.tags.manage", "Add and remove knowledge article tags."),
    PermissionDef(
        "knowledge.visibility.manage", "Manage which staff/department/role can see an article."
    ),
    PermissionDef("knowledge.assign", "Assign articles to staff, departments, or roles."),
    PermissionDef("knowledge.acknowledge", "Acknowledge an assigned mandatory article."),
    PermissionDef("knowledge.analytics.view", "View knowledge base completion analytics."),
    # Staff Operations — new in Phase 11, extending the Phase 3 `staff.view`/
    # `staff.manage`/`staff.hr_sensitive.read` triple (kept as-is for staff
    # *account* administration) with the operational HR domains this
    # phase's own instruction covers. `.disciplinary.*` is deliberately
    # separate from the broader `staff.hr_sensitive.read` — PROJECT_PLAN.md's
    # own "Disciplinary records with strict permissions" bullet calls for a
    # narrower grant than general HR-sensitive field visibility.
    PermissionDef("staff.profile.view", "View a staff member's operational employment profile."),
    PermissionDef("staff.profile.manage", "Edit a staff member's operational employment profile."),
    PermissionDef("staff.documents.view", "View staff HR documents.", is_sensitive=True),
    PermissionDef(
        "staff.documents.manage", "Upload and verify staff HR documents.", is_sensitive=True
    ),
    PermissionDef("staff.onboarding.view", "View onboarding plans and steps."),
    PermissionDef("staff.onboarding.manage", "Create and manage onboarding plans."),
    PermissionDef(
        "staff.offboarding.manage", "Create and manage offboarding plans.", is_sensitive=True
    ),
    PermissionDef("staff.shifts.view", "View shift templates and the roster."),
    PermissionDef("staff.shifts.manage", "Create and edit shift templates and roster assignments."),
    PermissionDef("staff.shifts.publish", "Publish the roster to staff."),
    PermissionDef("staff.shift_changes.request", "Request a shift swap, cover, or change."),
    PermissionDef("staff.shift_changes.approve", "Approve or reject shift change requests."),
    PermissionDef("staff.attendance.view", "View attendance records."),
    PermissionDef("staff.attendance.manage", "Record attendance."),
    PermissionDef(
        "staff.attendance.correct", "Correct a recorded attendance entry.", is_sensitive=True
    ),
    PermissionDef("staff.leave.view", "View leave requests."),
    PermissionDef("staff.leave.request", "Submit a leave request."),
    PermissionDef("staff.leave.approve", "Approve or reject leave requests.", is_sensitive=True),
    PermissionDef("staff.training.view", "View training courses and assignments."),
    PermissionDef("staff.training.manage", "Create and edit training courses."),
    PermissionDef("staff.training.assign", "Assign training courses to staff."),
    PermissionDef("staff.training.review", "Record training attempt scores and outcomes."),
    PermissionDef("staff.certifications.view", "View staff certifications."),
    PermissionDef("staff.certifications.manage", "Record and verify staff certifications."),
    PermissionDef("staff.skills.view", "View the staff skills matrix."),
    PermissionDef("staff.skills.manage", "Record and verify staff skills."),
    PermissionDef("staff.reviews.view", "View performance reviews.", is_sensitive=True),
    PermissionDef(
        "staff.reviews.manage",
        "Create, submit, and finalize performance reviews.",
        is_sensitive=True,
    ),
    PermissionDef("staff.disciplinary.view", "View staff disciplinary records.", is_sensitive=True),
    PermissionDef(
        "staff.disciplinary.manage", "Record staff disciplinary actions.", is_sensitive=True
    ),
    PermissionDef("staff.availability.view", "View staff availability windows."),
    PermissionDef("staff.availability.manage", "Record staff availability windows."),
    PermissionDef("staff.analytics.view", "View staff operations analytics."),
    # Loyalty — Phase 12, replacing the Phase 3 loyalty.view/.adjust
    # placeholder pair with the full domain (GROWTH_AND_INTELLIGENCE.md §5).
    PermissionDef("loyalty.view", "View loyalty programs, tiers, and accounts."),
    PermissionDef("loyalty.manage", "Create and edit loyalty programs and tiers."),
    PermissionDef("loyalty.adjust", "Earn/redeem points and issue manual adjustments."),
    PermissionDef(
        "loyalty.reverse",
        "Reverse a loyalty ledger entry via a compensating entry.",
        is_sensitive=True,
    ),
    PermissionDef("loyalty.tiers.manage", "Manually assign or review customer loyalty tiers."),
    PermissionDef("loyalty.analytics.view", "View loyalty program analytics."),
    # Segments — Phase 12 (GROWTH_AND_INTELLIGENCE.md §4).
    PermissionDef("segments.view", "View customer segments and membership."),
    PermissionDef("segments.manage", "Create and edit customer segments."),
    PermissionDef("segments.refresh", "Materialize a dynamic segment's current membership."),
    PermissionDef("segments.export", "Export segment membership.", is_sensitive=True),
    # Offers, coupons, and promotions — Phase 12 (GROWTH_AND_INTELLIGENCE.md §6).
    PermissionDef("offers.view", "View offers, coupons, and redemption history."),
    PermissionDef("offers.manage", "Create and edit offers and coupons."),
    PermissionDef("offers.approve", "Approve an offer requiring approval.", is_sensitive=True),
    PermissionDef("offers.redeem", "Reserve and confirm an offer redemption on an order."),
    PermissionDef("offers.reverse", "Reverse a confirmed offer redemption.", is_sensitive=True),
    PermissionDef("offers.analytics.view", "View offer and promotion analytics."),
    # Campaigns — Phase 12, replacing the Phase 3 campaigns.view/.create/
    # .approve/.send placeholder set (GROWTH_AND_INTELLIGENCE.md §3).
    PermissionDef("campaigns.view", "View marketing campaigns."),
    PermissionDef("campaigns.manage", "Create and edit marketing campaigns."),
    PermissionDef("campaigns.approve", "Approve a marketing campaign.", is_sensitive=True),
    PermissionDef(
        "campaigns.execute", "Schedule and execute a marketing campaign.", is_sensitive=True
    ),
    PermissionDef("campaigns.cancel", "Pause or cancel a running campaign."),
    PermissionDef("campaigns.analytics.view", "View campaign delivery and attribution analytics."),
    # Referrals — Phase 12 (GROWTH_AND_INTELLIGENCE.md §7).
    PermissionDef("referrals.view", "View referral programs, codes, and relationships."),
    PermissionDef("referrals.manage", "Create and edit referral programs and codes."),
    PermissionDef(
        "referrals.review",
        "Review and reject flagged referral relationships.",
        is_sensitive=True,
    ),
    PermissionDef(
        "referrals.adjust",
        "Manually adjust a referral relationship's reward.",
        is_sensitive=True,
    ),
    # Achievements and badges — Phase 12 (GROWTH_AND_INTELLIGENCE.md §8).
    PermissionDef("achievements.view", "View achievement definitions and customer awards."),
    PermissionDef("achievements.manage", "Create and edit achievement definitions."),
    # Gift cards — Phase 12 (GROWTH_AND_INTELLIGENCE.md §9).
    PermissionDef("gift_cards.view", "View gift cards and ledger history (masked codes)."),
    PermissionDef("gift_cards.issue", "Issue and activate a gift card.", is_sensitive=True),
    PermissionDef("gift_cards.manage", "Redeem a gift card against an order."),
    PermissionDef(
        "gift_cards.adjust", "Manually adjust or suspend a gift card.", is_sensitive=True
    ),
    PermissionDef(
        "gift_cards.reverse", "Reverse a gift card redemption or adjustment.", is_sensitive=True
    ),
    PermissionDef(
        "gift_cards.reveal_sensitive",
        "View an unmasked gift card code or PIN.",
        is_sensitive=True,
    ),
    PermissionDef(
        "gift_cards.analytics.view", "View gift card liability and redemption analytics."
    ),
    # Internal customer credit — Phase 12 (GROWTH_AND_INTELLIGENCE.md §10).
    PermissionDef("customer_credit.view", "View internal customer credit accounts and ledger."),
    PermissionDef("customer_credit.issue", "Issue internal customer credit.", is_sensitive=True),
    PermissionDef(
        "customer_credit.adjust", "Manually adjust internal customer credit.", is_sensitive=True
    ),
    PermissionDef(
        "customer_credit.approve",
        "Approve internal credit issuance above threshold.",
        is_sensitive=True,
    ),
    PermissionDef(
        "customer_credit.reverse",
        "Reverse an internal customer credit entry.",
        is_sensitive=True,
    ),
    PermissionDef(
        "customer_credit.analytics.view", "View internal customer credit liability analytics."
    ),
    # Commercial risk — Phase 12, a lightweight review queue for flagged
    # commercial events (GROWTH_AND_INTELLIGENCE.md §21).
    PermissionDef("commercial_risk.view", "View flagged commercial-risk events."),
    PermissionDef(
        "commercial_risk.review",
        "Resolve or dismiss a flagged commercial-risk event.",
        is_sensitive=True,
    ),
    # Feedback and reviews — Phase 13 (GROWTH_AND_INTELLIGENCE.md §11).
    # Replaces the Phase-3-era placeholder pair ("feedback.view",
    # "complaints.manage") with the granular set this phase actually needs,
    # the same replace-not-alias treatment every prior phase's own
    # placeholder codes got (e.g. Phase 6's "menu.manage").
    PermissionDef("feedback.view", "View customer feedback."),
    PermissionDef("feedback.create", "Record a new feedback entry."),
    PermissionDef("feedback.update", "Triage, acknowledge, tag, and edit a feedback entry."),
    PermissionDef("feedback.resolve", "Resolve, dismiss, or archive a feedback entry."),
    PermissionDef("feedback.convert_to_complaint", "Convert a feedback entry into a complaint."),
    PermissionDef("feedback.analytics.view", "View feedback and rating analytics."),
    PermissionDef(
        "feedback.request_review", "Create and manage post-order/post-reservation review requests."
    ),
    PermissionDef(
        "feedback.respond_to_review", "Draft an internal response to a public review reference."
    ),
    # Complaints and service recovery — Phase 13 (GROWTH_AND_INTELLIGENCE.md
    # §12). `complaints.view` sees complaints assigned to the actor's own
    # staff/department scope; `complaints.view_all` additionally sees every
    # complaint regardless of assignment (mirrors `staff.view`/
    # `staff.hr_sensitive.read`'s base-plus-sensitive-overlay shape).
    PermissionDef(
        "complaints.view", "View complaints assigned to your own staff or department scope."
    ),
    PermissionDef("complaints.view_all", "View every complaint regardless of assignment."),
    PermissionDef("complaints.create", "Create a new complaint."),
    PermissionDef("complaints.update", "Edit complaint details, add notes and attachments."),
    PermissionDef("complaints.assign", "Assign or reassign a complaint to staff or a department."),
    PermissionDef(
        "complaints.transition", "Move a complaint through its ordinary status lifecycle."
    ),
    PermissionDef(
        "complaints.escalate", "Manually escalate a complaint to the next level.", is_sensitive=True
    ),
    PermissionDef("complaints.resolve", "Mark a complaint resolved."),
    PermissionDef("complaints.close", "Close a resolved complaint."),
    PermissionDef("complaints.reopen", "Reopen a closed or resolved complaint."),
    PermissionDef("complaints.sla.manage", "Create and edit SLA policies."),
    PermissionDef("complaints.analytics.view", "View complaint and SLA analytics."),
    PermissionDef(
        "complaints.hr_sensitive.read",
        "View staff-conduct complaint detail beyond the base complaint record.",
        is_sensitive=True,
    ),
    # Service recovery — Phase 13 (GROWTH_AND_INTELLIGENCE.md §12.6).
    # Compensation is never mutated directly from these permissions alone —
    # `recovery.execute` only authorizes calling the already-permission-
    # gated `app.loyalty`/`app.customer_credit`/`app.orders` services that
    # actually record the value (PROJECT_PLAN.md's Phase 13 scope bullet).
    PermissionDef("recovery.view", "View service recovery actions."),
    PermissionDef("recovery.propose", "Propose a service recovery action on a complaint."),
    PermissionDef(
        "recovery.approve",
        "Approve a service recovery action requiring approval.",
        is_sensitive=True,
    ),
    PermissionDef("recovery.reject", "Reject a proposed service recovery action."),
    PermissionDef(
        "recovery.execute", "Execute an approved service recovery action.", is_sensitive=True
    ),
    PermissionDef(
        "recovery.reverse", "Reverse a completed service recovery action.", is_sensitive=True
    ),
    PermissionDef("recovery.rules.manage", "Create and edit compensation approval rules."),
    PermissionDef(
        "recovery.financial_sensitive.read",
        "View compensation value and approval detail beyond the base recovery record.",
        is_sensitive=True,
    ),
    # Staff, roles, and permissions
    PermissionDef("staff.view", "View staff user directory."),
    PermissionDef("staff.manage", "Manage staff user accounts.", is_sensitive=True),
    PermissionDef("staff.hr_sensitive.read", "Read HR-sensitive staff fields.", is_sensitive=True),
    PermissionDef("roles.view", "View roles and permissions."),
    PermissionDef(
        "roles.manage", "Manage role-permission and staff-role assignments.", is_sensitive=True
    ),
    # Analytics — Phase 14 (GROWTH_AND_INTELLIGENCE.md section 13.2). One
    # domain-scoped view code per reporting area exposed on a dashboard,
    # consolidated where two areas are always granted together in practice
    # (marketing+loyalty, feedback+complaints) rather than one code per
    # entry in `REPORTING_AREAS`. Named `analytics.<area>.view` (not
    # `analytics.view_<area>`) so every one of these ends in the `.view`
    # suffix `role_matrix._ALL_VIEW` scans for — the same auto-inclusion
    # mechanism `read_only_auditor` already relies on for every other
    # domain. `analytics.staff.view` and `analytics.system_operations.view`
    # are marked sensitive since they expose HR/operational-security-
    # adjacent aggregates respectively.
    PermissionDef("analytics.executive.view", "View the executive growth dashboard."),
    PermissionDef("analytics.sales.view", "View sales and revenue analytics."),
    PermissionDef("analytics.orders.view", "View order-operations analytics."),
    PermissionDef("analytics.customers.view", "View customer and lifecycle analytics."),
    PermissionDef("analytics.leads.view", "View lead-pipeline analytics."),
    PermissionDef("analytics.reservations.view", "View reservation analytics."),
    PermissionDef("analytics.inventory.view", "View inventory and supplier analytics."),
    PermissionDef(
        "analytics.marketing_loyalty.view", "View marketing, loyalty, and campaign analytics."
    ),
    PermissionDef("analytics.feedback_complaints.view", "View feedback and complaint analytics."),
    PermissionDef("analytics.staff.view", "View staff-operations analytics.", is_sensitive=True),
    PermissionDef(
        "analytics.system_operations.view",
        "View system-operations and integration-health analytics.",
        is_sensitive=True,
    ),
    # Reports — GROWTH_AND_INTELLIGENCE.md section 13.18-13.19.
    # `reports.drilldown.view` gates record-level drill-down data behind a
    # report/dashboard card, since it exposes more granular detail than the
    # aggregate metric itself.
    PermissionDef("reports.view", "View reports."),
    PermissionDef("reports.create", "Create custom report definitions."),
    PermissionDef(
        "reports.manage_system", "Edit or retire system report definitions.", is_sensitive=True
    ),
    PermissionDef("reports.share", "Share a report definition with other staff or roles."),
    PermissionDef("reports.run", "Execute a report run."),
    PermissionDef("reports.export", "Export reports.", is_sensitive=True),
    PermissionDef("reports.schedule", "Create and manage scheduled reports."),
    PermissionDef(
        "reports.schedule.manage_recipients",
        "Change who receives a scheduled report.",
        is_sensitive=True,
    ),
    PermissionDef("reports.delivery.view", "View scheduled-report delivery history."),
    PermissionDef(
        "reports.drilldown.view",
        "View record-level drill-down data behind a report.",
        is_sensitive=True,
    ),
    # Anomalies and forecasts — GROWTH_AND_INTELLIGENCE.md section 15.
    PermissionDef("anomalies.view", "View detected anomalies."),
    PermissionDef(
        "anomalies.manage_rules", "Create and edit anomaly-detection rules.", is_sensitive=True
    ),
    PermissionDef(
        "anomalies.acknowledge", "Acknowledge, investigate, resolve, or dismiss an anomaly."
    ),
    PermissionDef("forecasts.view", "View forecasts."),
    PermissionDef("forecasts.manage", "Create and edit forecast definitions.", is_sensitive=True),
    PermissionDef("forecasts.run", "Manually trigger a forecast generation."),
    # Controlled AI — GROWTH_AND_INTELLIGENCE.md section 14, CLAUDE.md
    # section 17. `ai.analytics.hr_sensitive` gates AI features from
    # including HR/staff-sensitive source data, mirroring
    # `staff.hr_sensitive.read`'s overlay pattern.
    PermissionDef(
        "ai.analytics.use", "Use controlled AI summary, draft, and explanation features."
    ),
    PermissionDef(
        "ai.analytics.query", "Ask a natural-language analytics question via controlled AI."
    ),
    PermissionDef(
        "ai.analytics.manage_prompts", "Manage controlled-AI prompt templates.", is_sensitive=True
    ),
    PermissionDef(
        "ai.analytics.usage.view",
        "View controlled-AI usage, cost, and performance reports.",
        is_sensitive=True,
    ),
    PermissionDef(
        "ai.analytics.hr_sensitive",
        "Allow controlled-AI features to include HR-sensitive source data.",
        is_sensitive=True,
    ),
    # Settings
    PermissionDef("settings.view", "View system settings."),
    PermissionDef("settings.manage", "Manage system settings.", is_sensitive=True),
    PermissionDef("settings.integrations.view", "View the integration registry and health status."),
    PermissionDef(
        "settings.integrations.update",
        "Update integration credentials and configuration.",
        is_sensitive=True,
    ),
    # Audit and system
    PermissionDef("audit.view", "View the audit trail.", is_sensitive=True),
    PermissionDef("system.health_view", "View system health status."),
    # Phase 15 — background jobs, scheduler, event bus, dead-letter recovery,
    # and cache. `settings.view`/`settings.manage` (above) cover feature
    # flags, operational settings, and maintenance mode — a dedicated
    # `settings.feature_flags.*`/`settings.operational.*` split was
    # considered and rejected as unnecessary permission-code sprawl for a
    # single-admin-surface concern; every code below is genuinely a
    # different domain (jobs, queues, scheduler, dead-letter, event log,
    # cache) that `settings.*` does not already name.
    PermissionDef("jobs.view", "View background job records and their status."),
    PermissionDef("jobs.manage", "Cancel or manually retry a background job.", is_sensitive=True),
    PermissionDef("queues.view", "View queue depth, throughput, and processing latency."),
    PermissionDef("scheduler.view", "View scheduled/recurring job configuration."),
    PermissionDef(
        "scheduler.manage",
        "Enable, disable, or manually trigger a scheduled job.",
        is_sensitive=True,
    ),
    PermissionDef("dead_letter.view", "View dead-lettered jobs and outbox events."),
    PermissionDef(
        "dead_letter.replay",
        "Replay or bulk-replay a dead-lettered job or event.",
        is_sensitive=True,
    ),
    PermissionDef("event_log.view", "View the domain event / outbox log."),
    PermissionDef("cache.view", "View cache statistics."),
    PermissionDef(
        "cache.invalidate", "Manually invalidate a cache key or family.", is_sensitive=True
    ),
)

PERMISSION_CODES: frozenset[str] = frozenset(p.code for p in PERMISSIONS)

if len(PERMISSION_CODES) != len(PERMISSIONS):
    raise RuntimeError("Duplicate permission code detected in the canonical registry.")


def get_permission(code: str) -> PermissionDef:
    for permission in PERMISSIONS:
        if permission.code == code:
            return permission
    raise KeyError(f"Unknown permission code: {code!r}")
