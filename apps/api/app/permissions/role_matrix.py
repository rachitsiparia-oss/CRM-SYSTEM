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
        "tasks.view",
        "tasks.view_all",
        "tasks.create",
        "tasks.update",
        "tasks.assign",
        "tasks.complete",
        "tasks.reopen",
        "tasks.delete",
        "notifications.manage",
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
        "communications.create",
        "communications.reply",
        "communications.assign",
        "communications.resolve",
        "communications.reopen",
        "communications.snooze",
        "communications.priority.manage",
        "communications.notes.create",
        "communications.templates.view",
        "communications.channels.view",
        "communications.analytics.view",
        "communications.call_logs.create",
        "communications.call_logs.view",
        "staff.view",
        "reports.view",
        "reports.export",
        # PROJECT_PLAN.md's "Recommended intent" for this phase names
        # operations_manager for "rosters, attendance, onboarding
        # operations and general knowledge" — the broadest non-HR staff-ops
        # authority, short of the HR-sensitive documents/disciplinary/
        # review grants reserved for hr_manager.
        "knowledge.view",
        "knowledge.create",
        "knowledge.update",
        "knowledge.review",
        "knowledge.approve",
        "knowledge.publish",
        "knowledge.archive",
        "knowledge.categories.manage",
        "knowledge.tags.manage",
        "knowledge.assign",
        "knowledge.acknowledge",
        "knowledge.analytics.view",
        "staff.profile.view",
        "staff.shifts.view",
        "staff.shifts.manage",
        "staff.shifts.publish",
        "staff.shift_changes.approve",
        "staff.attendance.view",
        "staff.attendance.manage",
        "staff.attendance.correct",
        "staff.onboarding.view",
        "staff.onboarding.manage",
        "staff.leave.view",
        "staff.leave.request",
        "staff.availability.view",
        "staff.training.view",
        "staff.certifications.view",
        "staff.skills.view",
        "staff.analytics.view",
        # Phase 12 — situational awareness across the commercial-growth
        # domains, matching the view-only oversight pattern already given
        # for inventory/reservations/communications above; program
        # ownership stays with marketing_manager, financial control with
        # finance_manager.
        "loyalty.view",
        "segments.view",
        "offers.view",
        "campaigns.view",
        "referrals.view",
        "achievements.view",
        "gift_cards.view",
        "customer_credit.view",
        "commercial_risk.view",
        # Phase 13 — operations owns end-to-end complaint case management
        # (assignment, escalation, ordinary resolution/closure) and mid-tier
        # recovery approval/execution; SLA policy design and HR-sensitive
        # detail stay with owner/general_manager/hr_manager respectively.
        "feedback.view",
        "feedback.create",
        "feedback.update",
        "feedback.resolve",
        "feedback.convert_to_complaint",
        "feedback.analytics.view",
        "feedback.request_review",
        "complaints.view_all",
        "complaints.create",
        "complaints.update",
        "complaints.assign",
        "complaints.transition",
        "complaints.escalate",
        "complaints.resolve",
        "complaints.close",
        "complaints.reopen",
        "complaints.analytics.view",
        "recovery.view",
        "recovery.propose",
        "recovery.approve",
        "recovery.execute",
        "recovery.financial_sensitive.read",
        # Phase 14 — broad operational reporting oversight, matching this
        # role's own broad operational grants above: every operational
        # dashboard, report creation/execution (not system-definition
        # management, reserved for owner/GM), and anomaly/forecast
        # visibility for the domains it already runs day to day.
        "analytics.executive.view",
        "analytics.orders.view",
        "analytics.reservations.view",
        "analytics.inventory.view",
        "analytics.feedback_complaints.view",
        "reports.view",
        "reports.create",
        "reports.run",
        "reports.export",
        "reports.drilldown.view",
        "anomalies.view",
        "anomalies.acknowledge",
        "forecasts.view",
        "ai.analytics.use",
    ),
    "finance_manager": (
        "dashboard.view",
        "tasks.view",
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
        "settings.integrations.view",
        "audit.view",
        # Phase 15 — operations_manager is the closest existing role to an
        # operational/IT-oversight role (it already holds settings.view and
        # audit.view), so it gets read-only visibility into the background
        # job/scheduler/event/cache surfaces. The sensitive mutation codes
        # (jobs.manage, scheduler.manage, dead_letter.replay,
        # cache.invalidate, settings.integrations.update) remain owner/
        # general_manager only, matching the settings.integrations.update
        # precedent already established for this role.
        "jobs.view",
        "queues.view",
        "scheduler.view",
        "dead_letter.view",
        "event_log.view",
        "cache.view",
        # Finance is explicitly excluded from broad HR access
        # ("Finance roles: no broad HR access unless explicitly
        # justified") — only the self-service basics every role gets.
        "knowledge.view",
        "knowledge.acknowledge",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        # Phase 12 — finance owns the money-denominated ledgers (gift
        # cards, internal credit) and every ledger reversal, since those
        # are real financial liability/write-off actions; program design
        # (loyalty tiers, offers, campaigns) stays with marketing_manager.
        "loyalty.view",
        "loyalty.analytics.view",
        "loyalty.reverse",
        "offers.view",
        "offers.analytics.view",
        "offers.reverse",
        "campaigns.analytics.view",
        "gift_cards.view",
        "gift_cards.issue",
        "gift_cards.manage",
        "gift_cards.adjust",
        "gift_cards.reverse",
        "gift_cards.reveal_sensitive",
        "gift_cards.analytics.view",
        "customer_credit.view",
        "customer_credit.issue",
        "customer_credit.adjust",
        "customer_credit.approve",
        "customer_credit.reverse",
        "customer_credit.analytics.view",
        "commercial_risk.view",
        "commercial_risk.review",
        # Phase 13 — finance signs off on and can reverse a compensation
        # action (the same "signs off on adjustments" pattern as
        # inventory.adjustments.approve above), and sees the financial
        # detail behind that decision; case management itself is
        # operations_manager/customer_support_agent's job.
        "complaints.view",
        "complaints.analytics.view",
        "recovery.view",
        "recovery.approve",
        "recovery.reverse",
        "recovery.financial_sensitive.read",
        # Phase 14 — finance owns revenue/cost reporting and controlled-AI
        # cost oversight (GROWTH_AND_INTELLIGENCE.md section 19's "finance
        # gets financial/revenue but not HR-sensitive staff analytics").
        # No `analytics.staff.view`, no `ai.analytics.hr_sensitive`.
        "analytics.executive.view",
        "analytics.sales.view",
        "analytics.orders.view",
        "analytics.inventory.view",
        "reports.view",
        "reports.create",
        "reports.run",
        "reports.export",
        "reports.schedule",
        "reports.drilldown.view",
        "forecasts.view",
        "anomalies.view",
        "ai.analytics.use",
        "ai.analytics.query",
        "ai.analytics.usage.view",
    ),
    "kitchen_manager": (
        "dashboard.view",
        "tasks.view",
        "tasks.create",
        "tasks.update",
        "tasks.assign",
        "tasks.complete",
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
        # Department-scoped staff operations and knowledge approval for the
        # kitchen department, per this phase's own instruction's
        # "Recommended intent" for department managers.
        "knowledge.view",
        "knowledge.create",
        "knowledge.update",
        "knowledge.review",
        "knowledge.approve",
        "knowledge.publish",
        "knowledge.tags.manage",
        "knowledge.assign",
        "knowledge.acknowledge",
        "staff.profile.view",
        "staff.shifts.view",
        "staff.shifts.manage",
        "staff.attendance.view",
        "staff.attendance.manage",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        "staff.training.assign",
        "staff.certifications.view",
        "staff.skills.view",
        "staff.skills.manage",
        "staff.availability.view",
        # Phase 13 — food_quality/allergy_or_dietary complaints route to the
        # kitchen department; the kitchen manager investigates and notes
        # root cause on complaints assigned to them, but does not own
        # intake, transitions, or recovery decisions.
        "feedback.view",
        "complaints.view",
        "complaints.update",
        # Phase 14 — kitchen manager needs its own inventory/recipe-cost
        # picture, not the full operational suite.
        "analytics.inventory.view",
        "reports.view",
    ),
    "inventory_manager": (
        "dashboard.view",
        "tasks.view",
        "tasks.create",
        "tasks.update",
        "tasks.complete",
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
        "knowledge.view",
        "knowledge.create",
        "knowledge.update",
        "knowledge.review",
        "knowledge.approve",
        "knowledge.publish",
        "knowledge.tags.manage",
        "knowledge.assign",
        "knowledge.acknowledge",
        "staff.profile.view",
        "staff.shifts.view",
        "staff.attendance.view",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        "staff.certifications.view",
        "staff.skills.view",
        # Phase 13 — supply/packaging-related complaints occasionally route
        # to inventory for awareness; no case-management authority.
        "complaints.view",
        # Phase 14 — the store keeper is the primary consumer of inventory
        # analytics, waste/consumption anomalies, and ingredient-demand
        # forecasts (a named GROWTH_AND_INTELLIGENCE.md section 15.2
        # forecast area).
        "analytics.inventory.view",
        "reports.view",
        "reports.run",
        "anomalies.view",
        "anomalies.acknowledge",
        "forecasts.view",
    ),
    "reservation_manager": (
        "dashboard.view",
        "tasks.view",
        "tasks.create",
        "tasks.update",
        "tasks.assign",
        "tasks.complete",
        "tasks.reopen",
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
        "communications.create",
        "communications.reply",
        "communications.assign",
        "communications.resolve",
        "communications.reopen",
        "communications.snooze",
        "communications.priority.manage",
        "communications.notes.create",
        "communications.templates.view",
        "communications.call_logs.create",
        "communications.call_logs.view",
        "staff.view",
        "knowledge.view",
        "knowledge.create",
        "knowledge.update",
        "knowledge.review",
        "knowledge.approve",
        "knowledge.publish",
        "knowledge.tags.manage",
        "knowledge.assign",
        "knowledge.acknowledge",
        "staff.profile.view",
        "staff.shifts.view",
        "staff.attendance.view",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        # Phase 12 — read-only awareness of offers that may affect
        # reservations/deposits (GROWTH_AND_INTELLIGENCE.md's own
        # integration note); no redemption or program-management authority.
        "offers.view",
        # Phase 13 — reservation-linked complaints (the "reservation"
        # category) are this role's domain, including proposing a priority-
        # reservation recovery; financial/escalation authority stays
        # elsewhere.
        "feedback.view",
        "complaints.view",
        "complaints.create",
        "complaints.update",
        "complaints.transition",
        "complaints.resolve",
        "recovery.view",
        "recovery.propose",
        # Phase 14 — reservation analytics and forecast for the domain this
        # role owns end to end (reservation volume is a named forecast
        # area).
        "analytics.reservations.view",
        "reports.view",
        "forecasts.view",
    ),
    "customer_support_agent": (
        "dashboard.view",
        "tasks.view",
        "tasks.create",
        "tasks.update",
        "tasks.complete",
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
        "communications.create",
        "communications.reply",
        "communications.resolve",
        "communications.reopen",
        "communications.snooze",
        "communications.notes.create",
        "communications.templates.view",
        "communications.preferences.view",
        "communications.call_logs.create",
        "communications.call_logs.view",
        # Phase 13 — the primary complaint intake and case-handling role:
        # full feedback lifecycle, ordinary complaint case management, and
        # proposing (not approving/executing) recovery actions. No
        # view_all, escalate, close, reopen, sla.manage, hr_sensitive,
        # analytics, or any recovery approval/execution/reversal authority.
        "feedback.view",
        "feedback.create",
        "feedback.update",
        "feedback.resolve",
        "feedback.convert_to_complaint",
        "feedback.request_review",
        "complaints.view",
        "complaints.create",
        "complaints.update",
        "complaints.transition",
        "complaints.resolve",
        "recovery.view",
        "recovery.propose",
        # "Customer support/reservation roles: operational knowledge access
        # relevant to their duties" plus self-service basics every role gets.
        "knowledge.view",
        "knowledge.acknowledge",
        "staff.shifts.view",
        "staff.shift_changes.request",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        # Phase 12 — service recovery is core to this role: small goodwill
        # loyalty adjustments, coupon/offer redemption at the customer's
        # request, gift-card lookup/redemption, and small internal-credit
        # issuance (staff-adjustment limits and any approval threshold are
        # enforced in app.customer_credit.service, not by this permission
        # alone). No reversal, no reveal-sensitive, no program design.
        "loyalty.view",
        "loyalty.adjust",
        "offers.view",
        "offers.redeem",
        "gift_cards.view",
        "gift_cards.manage",
        "customer_credit.view",
        "customer_credit.issue",
        "referrals.view",
        "achievements.view",
        # Phase 14 — front-line visibility into the feedback/complaint
        # signal this role generates, and the controlled-AI reply-drafting/
        # conversation-summary capabilities that directly support their
        # existing `communications.reply` work.
        "analytics.feedback_complaints.view",
        "reports.view",
        "ai.analytics.use",
    ),
    "marketing_manager": (
        "dashboard.view",
        "tasks.view",
        "tasks.create",
        # Phase 12 — marketing_manager is the primary owner of this entire
        # commercial-growth domain (loyalty program/tier design, segments,
        # offers/coupons, campaigns, referrals, achievements). Money-
        # denominated ledger custody (gift-card issuance/reversal, internal
        # credit issuance/approval/reversal, any loyalty/offer *reversal*)
        # stays with finance_manager — see that role's own comment.
        "loyalty.view",
        "loyalty.manage",
        "loyalty.adjust",
        "loyalty.tiers.manage",
        "loyalty.analytics.view",
        "segments.view",
        "segments.manage",
        "segments.refresh",
        "segments.export",
        "offers.view",
        "offers.manage",
        "offers.approve",
        "offers.analytics.view",
        "campaigns.view",
        "campaigns.manage",
        "campaigns.approve",
        "campaigns.execute",
        "campaigns.cancel",
        "campaigns.analytics.view",
        "referrals.view",
        "referrals.manage",
        "referrals.review",
        "referrals.adjust",
        "achievements.view",
        "achievements.manage",
        "gift_cards.view",
        "gift_cards.manage",
        "gift_cards.analytics.view",
        "customer_credit.view",
        "customer_credit.analytics.view",
        "commercial_risk.view",
        "customers.view",
        "customers.tags.manage",
        "leads.view",
        "leads.notes.manage",
        "leads.export",
        "reports.view",
        "communications.view",
        "communications.templates.view",
        "communications.templates.manage",
        "communications.preferences.view",
        "communications.preferences.manage",
        "communications.suppressions.view",
        "communications.analytics.view",
        # Marketing owns the marketing-guidelines knowledge category.
        "knowledge.view",
        "knowledge.create",
        "knowledge.update",
        "knowledge.tags.manage",
        "knowledge.acknowledge",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        # Phase 13 — marketing owns review-request outreach and drafting
        # public-review responses, plus the aggregate feedback/complaint-
        # rate signal that feeds its own reports; no complaint case
        # management.
        "feedback.view",
        "feedback.analytics.view",
        "feedback.request_review",
        "feedback.respond_to_review",
        "complaints.analytics.view",
        # Phase 14 — marketing owns campaign/customer-growth analytics and
        # reporting end to end (GROWTH_AND_INTELLIGENCE.md section 19:
        # "marketing gets campaign/segment/loyalty/feedback/customer-growth
        # analytics"), plus campaign-response forecasting and campaign/
        # complaint-rate anomaly review, and drafting/summary AI features
        # for campaign copy and feedback themes.
        "analytics.marketing_loyalty.view",
        "analytics.customers.view",
        "analytics.leads.view",
        "analytics.feedback_complaints.view",
        "reports.view",
        "reports.create",
        "reports.run",
        "reports.export",
        "reports.schedule",
        "reports.share",
        "reports.drilldown.view",
        "forecasts.view",
        "anomalies.view",
        "ai.analytics.use",
        "ai.analytics.query",
    ),
    "hr_manager": (
        "dashboard.view",
        "tasks.view",
        "tasks.view_all",
        "tasks.create",
        "tasks.assign",
        "notifications.manage",
        "staff.view",
        "staff.manage",
        "staff.hr_sensitive.read",
        "roles.view",
        "roles.manage",
        "audit.view",
        # The broadest staff-operations authority — the full HR-sensitive
        # domain (documents, disciplinary, reviews) that no other role
        # gets, plus the HR side of onboarding/offboarding, training,
        # certifications, and skills. Day-to-day floor roster/attendance
        # *operation* stays with operations_manager/shift_supervisor; HR
        # still needs read visibility into both for planning.
        "knowledge.view",
        "knowledge.create",
        "knowledge.update",
        "knowledge.review",
        "knowledge.approve",
        "knowledge.publish",
        "knowledge.archive",
        "knowledge.categories.manage",
        "knowledge.tags.manage",
        "knowledge.visibility.manage",
        "knowledge.assign",
        "knowledge.acknowledge",
        "knowledge.analytics.view",
        "staff.profile.view",
        "staff.profile.manage",
        "staff.documents.view",
        "staff.documents.manage",
        "staff.onboarding.view",
        "staff.onboarding.manage",
        "staff.offboarding.manage",
        "staff.shifts.view",
        "staff.attendance.view",
        "staff.leave.view",
        "staff.leave.request",
        "staff.leave.approve",
        "staff.training.view",
        "staff.training.manage",
        "staff.training.assign",
        "staff.training.review",
        "staff.certifications.view",
        "staff.certifications.manage",
        "staff.skills.view",
        "staff.skills.manage",
        "staff.reviews.view",
        "staff.reviews.manage",
        "staff.disciplinary.view",
        "staff.disciplinary.manage",
        "staff.availability.view",
        "staff.availability.manage",
        "staff.analytics.view",
        # Phase 13 — staff-conduct ("staff_behavior") complaints are HR's
        # domain regardless of who they happen to be assigned to; the
        # hr_sensitive overlay unlocks the sensitive detail on top of the
        # base record, the same base-plus-sensitive-overlay shape as
        # staff.view/.hr_sensitive.read above.
        "feedback.view",
        "complaints.view_all",
        "complaints.hr_sensitive.read",
        "complaints.update",
        "complaints.transition",
        "complaints.resolve",
        "complaints.close",
        # Phase 14 — staff analytics without unrelated financial control
        # (GROWTH_AND_INTELLIGENCE.md section 19's explicit HR reasoning),
        # plus the AI HR-sensitive overlay so controlled-AI features may
        # draw on HR-sensitive source data for this role alone.
        "analytics.staff.view",
        "reports.view",
        "reports.export",
        "ai.analytics.use",
        "ai.analytics.hr_sensitive",
    ),
    "shift_supervisor": (
        "dashboard.view",
        "tasks.view",
        "tasks.create",
        "tasks.update",
        "tasks.assign",
        "tasks.complete",
        "communications.view",
        "communications.call_logs.create",
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
        # "Shift Supervisors: roster and attendance operational access
        # without sensitive HR access" — this phase's own instruction's
        # "Recommended intent".
        "knowledge.view",
        "knowledge.acknowledge",
        "staff.shifts.view",
        "staff.shifts.manage",
        "staff.shift_changes.request",
        "staff.shift_changes.approve",
        "staff.attendance.view",
        "staff.attendance.manage",
        "staff.leave.view",
        "staff.leave.request",
        "staff.availability.view",
        # Phase 12 — floor supervisor handles checkout-time coupon/gift-
        # card redemption and can flag suspicious activity to management;
        # no program design, no financial-reversal authority.
        "offers.view",
        "offers.redeem",
        "gift_cards.view",
        "gift_cards.manage",
        "loyalty.view",
        "commercial_risk.view",
        # Phase 13 — floor-level intake: log a complaint or feedback on the
        # spot and add notes; formal case progression stays with support/
        # operations.
        "feedback.view",
        "feedback.create",
        "complaints.view",
        "complaints.create",
        "complaints.update",
        "recovery.view",
        "recovery.propose",
    ),
    "kitchen_staff": (
        "dashboard.view",
        "tasks.view",
        "tasks.complete",
        "orders.view",
        "orders.transition",
        "menu.view",
        # Quantities and recipes only — no costs, no approvals, no master
        # data. Recording wastage is the one stock write a line cook needs.
        "inventory.view",
        "inventory.recipes.view",
        "inventory.wastage.create",
        # "Front-of-House/Kitchen Staff: self-service schedule, leave,
        # training and general knowledge access" — this phase's own
        # instruction's "Recommended intent".
        "knowledge.view",
        "knowledge.acknowledge",
        "staff.shifts.view",
        "staff.shift_changes.request",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        "staff.skills.view",
    ),
    "front_of_house_staff": (
        "dashboard.view",
        "tasks.view",
        "tasks.create",
        "tasks.complete",
        "communications.view",
        "communications.create",
        "communications.reply",
        "communications.notes.create",
        "communications.call_logs.create",
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
        "knowledge.view",
        "knowledge.acknowledge",
        "staff.shifts.view",
        "staff.shift_changes.request",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        "staff.skills.view",
        # Phase 12 — front-of-house is the primary checkout-time redemption
        # point for coupons and gift cards; loyalty is visible so they can
        # answer balance questions, but not adjustable by this role.
        "offers.view",
        "offers.redeem",
        "gift_cards.view",
        "gift_cards.manage",
        "loyalty.view",
        # Phase 13 — first point of contact for a guest complaint or piece
        # of feedback; formal case progression stays with support/
        # operations/reservation_manager.
        "feedback.view",
        "feedback.create",
        "complaints.view",
        "complaints.create",
    ),
    "delivery_coordinator": (
        "dashboard.view",
        "tasks.view",
        "tasks.complete",
        "orders.view",
        "orders.transition",
        "orders.complete",
        "communications.view",
        "communications.reply",
        "communications.call_logs.create",
        "communications.call_logs.view",
        "knowledge.view",
        "knowledge.acknowledge",
        "staff.shifts.view",
        "staff.shift_changes.request",
        "staff.leave.view",
        "staff.leave.request",
        "staff.training.view",
        # Phase 13 — delivery/delay/packaging complaints are this role's
        # domain end to end; no financial or escalation authority.
        "feedback.view",
        "complaints.view",
        "complaints.create",
        "complaints.update",
        "complaints.transition",
        "complaints.resolve",
    ),
    "read_only_auditor": tuple(sorted({*_ALL_VIEW, "audit.view"})),
}

_unknown_codes = {
    code for codes in ROLE_PERMISSIONS.values() for code in codes if code not in PERMISSION_CODES
}
if _unknown_codes:
    raise RuntimeError(f"role_matrix references unknown permission codes: {_unknown_codes!r}")
