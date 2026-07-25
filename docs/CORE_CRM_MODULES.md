# RKPR RESTAURANT CRM — CORE CRM MODULES

## 1. DOCUMENT PURPOSE

This document defines the complete product behavior, user experience, workflows, business rules, permissions, data presentation, validation, edge cases, operational states, and acceptance criteria for the core modules of the RKPR Restaurant CRM.

It must remain fully consistent with `CLAUDE.md`, `PROJECT_PLAN.md`, `ARCHITECTURE_AND_TECH_STACK.md`, and `DATABASE_AND_API.md`.

This document is product-authoritative. It explains what users can see and do, how each module behaves, how records move through their lifecycle, what data must be displayed, what actions must be protected, how failures are handled, and what "done" means for each core module.

The core modules covered here are:

1. Dashboard
2. Customers
3. Leads
4. Orders & Restaurant Operations
5. Menu & Products
6. Inventory & Suppliers
7. Reservations & Calendar

Dummy data must remain identical to `PROJECT_PLAN.md`. Dummy information is permitted only for business profiles, menu items, prices, staff examples, customers, leads, suppliers, inventory levels, orders, reservations, reports, and seed fixtures. Architecture, security, tools, libraries, provider capabilities, API behavior, and deployment decisions are never dummy.

## 2. GLOBAL PRODUCT RULES FOR ALL CORE MODULES

### 2.1 Fast interaction

- Primary screens must load useful content immediately.
- No module may block the interface while reports, exports, AI analysis, file processing, campaign jobs, or large imports run.
- All tables are server-paginated.
- Search is debounced and server-side.
- Filters are explicit, indexed, and reflected in the URL where practical.
- Large datasets must use virtualized rendering when needed.
- Skeletons must preserve layout and avoid excessive shifting.
- Realtime updates must patch scoped records rather than force full-page reloads.
- Heavy charts use pre-aggregated endpoints.
- No screen may fetch all customers, orders, messages, stock movements, or audit events into the browser.

### 2.2 Security and permissions

- Backend permission checks are authoritative, using the single canonical capability registry defined in `DATABASE_AND_API.md` §4.4.
- Navigation visibility may reflect permissions, but hidden navigation is never treated as security.
- Sensitive actions require explicit permission and audit logging.
- Financial adjustments, refunds, inventory corrections, customer merges, staff access changes, integration settings, loyalty adjustments, and exports are treated as sensitive.
- Every record-detail route must protect against insecure direct object reference.
- Private files are served only through short-lived, permission-checked signed URLs.
- Sensitive data must be omitted from list responses when not required.

### 2.3 Data consistency

- Every module must use the enum values and state transitions defined in `DATABASE_AND_API.md`.
- No UI may invent a status unavailable to the backend.
- Human-readable numbers must remain stable after creation.
- Historical orders retain product, variant, modifier, price, tax, and discount snapshots even after menu changes.
- Financial totals are always returned by the backend as integer minor units.
- Inventory totals are derived from the ledger and controlled summaries, not arbitrary browser calculations.
- Customer lifetime value and order counts update only after eligible completed orders.

### 2.4 Shared user-interface patterns

All major modules use the following standard page layout where applicable:

- Page title and concise operational subtitle
- Primary action button
- Date or scope selector when useful
- Saved views
- Search
- Filter drawer or filter bar
- Summary metrics
- Main table, board, calendar, or operational queue
- Bulk-action toolbar that appears only after selection
- Record details in a dedicated page or side panel depending on complexity
- Activity timeline for important records
- Empty state with a meaningful action
- Error state with retry and request ID
- Permission-denied state without exposing protected content

### 2.5 Shared record states

Every screen must visually distinguish:

- Active records
- Archived or soft-deleted records
- Failed records
- Records requiring review
- Records with unresolved conflicts
- Records with overdue actions
- Records updated by another user while open

### 2.6 Shared bulk-action rules

Bulk actions must:

- Require explicit user selection
- Display the number of affected records
- Respect permissions record by record
- Show a preview when the action is sensitive
- Avoid partial silent failure
- Return a result summary with succeeded, skipped, and failed counts
- Never allow unbounded "select every record in the database" without a server-side job and explicit confirmation

### 2.7 Shared import and export rules

- Imports require template validation, column mapping, preview, duplicate review, error reporting, and final confirmation.
- Imports must be resumable or safely repeatable where practical.
- Large imports run asynchronously in the ARQ worker.
- Exports are generated asynchronously for large ranges.
- Export files expire and remain private.
- Export filters, requester, row count, generated time, and download events are audited.

### 2.8 Shared activity timeline

A timeline entry should include:

- event type
- plain-language summary
- actor
- source
- timestamp in `Asia/Kolkata`
- safe metadata
- linked record where applicable

Timelines must not expose secrets, raw provider payloads, access tokens, hidden HR details, or unrestricted internal notes.

## 3. DASHBOARD MODULE

### 3.1 Purpose

The Dashboard is the operational command center for RKPR Fast-Food Restaurant. It must help owners, managers, and authorized staff understand current business conditions without opening several modules.

It is not a decorative analytics page. It must surface urgent operational work, current sales, order flow, reservation workload, lead follow-ups, customer health, inventory risk, staff tasks, and system issues.

### 3.2 Primary user groups

- Owner
- General Manager
- Operations Manager
- Finance Manager
- Kitchen Manager
- Inventory Manager
- Reservation Manager
- Marketing Manager
- Shift Supervisor
- Customer Support Agent

The dashboard adapts to permissions. Users see only metrics and actions they are authorized to access.

### 3.3 Time scopes

Supported scopes:

- Today
- Yesterday
- Last 7 days
- Last 30 days
- This month
- Previous month
- Custom date range

Operational widgets such as active orders, current reservations, low stock, unread messages, and overdue follow-ups remain current even when a historical analytics range is selected.

### 3.4 Global dashboard header

Must include:

- selected date range
- last successful data refresh
- manual refresh control
- export summary action where permitted
- notification bell
- current user menu
- business operating status: open, closing soon, closed, special hours
- integration health badge only when useful

### 3.5 Executive KPI cards

Default owner and manager KPI cards:

- Gross sales
- Net sales
- Completed orders
- Average order value
- New customers
- Repeat customer rate
- Reservation covers
- Lead conversion rate

Each card includes:

- current value
- comparison value
- percentage or absolute change
- clear comparison period
- trend direction
- data tooltip
- link to relevant filtered module

Financial KPI cards must state whether taxes, refunds, discounts, platform fees, and delivery charges are included.

### 3.6 Live operations strip

Displays:

- orders awaiting acceptance
- orders preparing
- orders delayed beyond target
- orders ready for pickup
- orders out for delivery
- reservations awaiting review
- guests arriving within 60 minutes
- critical-stock items
- unread customer conversations
- overdue lead follow-ups
- unresolved high-severity complaints

Each item must link to the exact filtered queue.

### 3.7 Sales overview

Required views:

- sales by day or hour
- sales by order channel
- sales by order type
- top categories
- top products
- discount impact
- refund impact

Channels must remain consistent:

- website
- mobile_web
- whatsapp_assisted
- phone_assisted
- pos_import
- zomato_import
- swiggy_import
- corporate
- event

The dashboard must distinguish direct sales from aggregator-imported sales.

### 3.8 Order operations widget

Displays:

- current active-order count
- median preparation time
- delayed-order count
- cancellation count
- refund-request count
- channel distribution

Queue rows show:

- order number
- source
- order type
- customer or guest label
- amount
- current status
- time in current status
- assigned staff
- SLA indicator

### 3.9 Reservation widget

Displays:

- today's approved reservations
- pending review
- arriving soon
- seated
- completed
- no-shows
- cancelled
- total covers
- peak reservation period

Reservation rows show:

- reservation number
- guest name
- time
- guest count
- seating zone
- approval state
- special-request indicator

Reservations are never automatically approved from the dashboard.

### 3.10 Customer health widget

Displays:

- new customers
- repeat customers
- loyal customers
- VIP customers
- at-risk customers
- dormant customers
- high-AOV customers
- complaint-recovery customers

Uses the exact segments defined in `DATABASE_AND_API.md`.

### 3.11 Lead pipeline widget

Displays:

- new leads
- contacted
- qualified
- interested
- follow-up scheduled
- proposal shared
- negotiating
- won
- lost

Also show:

- total estimated pipeline value
- leads with overdue follow-ups
- lead source distribution
- top assigned staff by active lead count

### 3.12 Inventory risk widget

Displays:

- low stock
- critical stock
- out of stock
- expiring soon
- quarantined
- overdue cycle counts
- purchase orders awaiting receipt

Each row shows:

- item name
- current stock
- reorder level
- unit
- preferred supplier
- days of cover when available
- affected menu items when practical

### 3.13 Staff and task widget

Displays only authorized information:

- on-shift staff
- unfilled shifts
- pending leave approvals
- expiring training records
- unresolved assigned tasks

Sensitive HR details must not appear on the general dashboard.

### 3.14 Communication widget

Displays:

- unread conversations
- conversations waiting for first response
- failed outbound messages
- messages requiring manual review
- complaint conversations

### 3.15 Marketing and loyalty widget

Displays:

- active campaigns
- scheduled campaigns
- recent campaign conversions
- new loyalty enrollments
- points earned
- points redeemed
- expiring points

### 3.16 Dashboard AI insights

AI insights are advisory and must be grounded in CRM data. AI credentials and integration are only introduced in Phase 14 — Reports, Analytics, and Controlled AI; this widget renders empty/disabled until then.

Allowed examples:

- unusual drop in direct orders
- increase in cancellation rate
- stock risk affecting top-selling menu items
- customers likely to become dormant
- leads needing attention
- products with declining margin
- likely peak period based on recent patterns

Requirements:

- clearly label AI-generated content
- include the supporting metrics and timeframe
- never execute operational changes automatically
- never invent unavailable data
- allow user feedback
- hide the panel when no useful insight exists

### 3.17 Quick actions

Permission-controlled quick actions:

- Create customer
- Create lead
- Create assisted order
- Add reservation request
- Record inventory receipt
- Add stock adjustment
- Create complaint
- Generate report

### 3.18 Dashboard refresh behavior

- Operational queues may update through scoped realtime events.
- KPI summaries refresh on interval or manual request.
- Reconnect must trigger authoritative re-fetch.
- Failed widgets must degrade independently; one failure must not blank the whole dashboard.
- Every widget includes a local retry action.

### 3.19 Dashboard empty states

Examples:

- No active orders: "No active orders right now."
- No pending reservations: "All reservation requests have been reviewed."
- No inventory risk: "No stock items currently require attention."
- No overdue leads: "No lead follow-ups are overdue."

### 3.20 Dashboard acceptance criteria

The module is complete only when:

- permissions shape visible widgets and underlying data
- financial metrics reconcile with report calculations
- operational queues are bounded
- realtime updates do not duplicate rows
- partial widget failures are isolated
- date comparisons are clearly labeled
- links open correct filtered views
- no dummy values are hardcoded into production components
- AI insights cite the actual supporting data

## 4. CUSTOMERS MODULE

### 4.1 Purpose

The Customers module provides a unified customer record across orders, reservations, communications, feedback, complaints, loyalty, notes, preferences, tags, addresses, and lead-conversion history.

It must help RKPR recognize repeat customers, understand preferences, improve service, resolve complaints, and run consent-aware marketing.

### 4.2 Customer list page

Columns:

- customer number
- display name
- phone
- email
- customer type
- segment
- status
- completed orders
- lifetime value
- average order value
- loyalty points
- last order
- assigned staff
- tags

Default view excludes soft-deleted customers.

### 4.3 Customer search

Search supports:

- customer number
- display name
- organization name
- normalized phone
- normalized email
- tag

Search must not expose records outside the user's permission scope.

### 4.4 Customer filters

- customer type
- active status
- segment
- assigned staff
- acquisition source
- dietary preference
- preferred channel
- loyalty enrolled
- minimum lifetime value
- completed-order range
- last-order range
- tag
- complaint history
- marketing consent state
- deleted state where permitted

### 4.5 Saved customer views

Examples:

- VIP customers
- At-risk repeat customers
- Dormant customers
- High-AOV customers
- Jain-preference customers
- Customers with active complaints
- Customers with birthdays this month
- Customers with expiring loyalty points

Saved views store filters and sort settings, not copied records.

### 4.6 Customer creation

Required minimum:

- display name or valid individual name fields
- at least one contact method when operationally required

Optional:

- customer type
- organization name
- phone
- email
- date of birth
- anniversary
- preferred language
- dietary preference
- spice preference
- address
- acquisition source
- assigned staff
- tags
- notes
- consent records

Before creation, the system must check possible duplicates using normalized phone and email.

### 4.7 Duplicate handling

When duplicates are detected:

- show possible matches
- show match reasons
- allow the user to open existing records
- allow creation only when permitted
- never automatically merge

Possible match reasons:

- exact normalized phone
- exact normalized email
- strong name and address similarity
- linked external customer identifier

### 4.8 Customer profile header

Displays:

- display name
- customer number
- type
- segment
- status
- key tags
- phone and email
- assigned staff
- loyalty balance
- lifetime value
- completed orders
- last order date
- unresolved complaint indicator

Primary actions:

- Edit
- Add note
- Add tag
- Start conversation
- Create assisted order
- Create reservation request
- Add complaint
- Adjust loyalty where permitted
- Merge customer where permitted
- Archive

### 4.9 Customer profile tabs

#### Overview

- identity
- contact details
- addresses
- preferences
- customer metrics
- loyalty summary
- recent activity
- active tasks
- alerts

#### Orders

- order number
- date
- channel
- order type
- status
- amount
- products
- refund state

#### Reservations

- reservation number
- date and time
- guest count
- status
- seating zone
- special requests

#### Communications

- channel
- conversation status
- last message
- assigned staff
- unread state

#### Feedback and complaints

- ratings
- comments
- complaint severity
- resolution state
- recovery action

#### Loyalty

- current points
- lifetime earned
- lifetime redeemed
- expiring points
- complete ledger

#### Notes and tags

- notes with type, author, and timestamp
- tags with assignment metadata

#### Audit

Visible only with permission (`audit.view`).

### 4.10 Customer metrics

- completed-order count
- lifetime value
- average order value
- first order date
- last order date
- preferred order channel
- most ordered category
- favorite product
- visit frequency
- refund count
- complaint count
- cancellation count
- reservation no-show count

Metrics must be calculated by backend services and clearly define eligibility.

### 4.11 Customer segments

Approved segments:

- new
- repeat
- loyal
- vip
- at_risk
- dormant
- high_aov
- family
- corporate
- college_group
- delivery_first
- dine_in_first
- discount_sensitive
- complaint_recovery

Segmentation may be rule-based and recalculated asynchronously. Manual overrides require reason and audit logging.

### 4.12 Dietary and preference data

Supported examples:

- vegetarian
- non-vegetarian
- vegan
- Jain
- allergen notes
- spice level
- preferred seating zone
- favorite product
- preferred order channel
- delivery instructions

Allergen data must be presented as customer-provided preference information, not as a guarantee that the kitchen is allergen-free.

### 4.13 Customer consents

Consent types:

- whatsapp_marketing
- email_marketing
- sms_marketing
- loyalty
- feedback_request
- personalization

Every consent record includes:

- status
- source
- policy version
- evidence
- granted time
- withdrawn time

Marketing actions must use the current consent state at send time.

### 4.14 Customer notes

Note types may include:

- general
- service_preference
- complaint
- recovery
- corporate
- delivery
- reservation
- dietary

Sensitive notes require dedicated permission.

Notes are append-oriented. Editing a note should create revision history or be restricted to a short correction window.

### 4.15 Customer merge workflow

Merge is a sensitive, transactional operation requiring the `customers.merge` permission.

Workflow:

1. Select source records.
2. Select surviving record.
3. Compare conflicting fields.
4. Choose retained values.
5. Preview linked records.
6. Confirm with reason.
7. Execute in one transaction.
8. Record merge event and audit log.

Linked records include:

- orders
- reservations
- conversations
- feedback
- complaints
- loyalty
- addresses
- tags
- notes
- consents
- lead history

The merge must not duplicate loyalty, financial, or activity effects.

### 4.16 Dummy customer fixtures

Use the same examples from `PROJECT_PLAN.md` and `DATABASE_AND_API.md`:

- Ananya Rao — vegetarian — 12 completed orders — favorite Paneer Tikka Pizza — 680 loyalty points
- Rahul Mehta — non-vegetarian — 8 completed orders — favorite Double Crunch Chicken Burger — at-risk
- Shreya Kulkarni — Jain preference — 5 completed orders — favorite Jain Aloo Crunch Burger
- BrightWave Technologies — corporate customer — monthly lunch orders — assigned to Nikhil Jain

These values are development fixtures only.

### 4.17 Customer bulk actions

Allowed where permission exists:

- assign staff
- add tag
- remove tag
- change segment override
- export
- create consent-safe campaign audience
- archive

Bulk loyalty adjustment and bulk merge are not ordinary bulk actions.

### 4.18 Customer edge cases

- customer with no phone but email
- customer with no email but phone
- walk-in customer with minimal identity
- corporate customer with multiple contacts
- shared family phone number
- changed phone number
- withdrawn consent
- merged duplicate
- deleted customer with historical orders
- customer requesting data correction
- customer with loyalty balance and refund
- customer with active complaint

### 4.19 Customer acceptance criteria

- duplicate warnings use normalized data
- profile aggregates reconcile with orders and loyalty ledger
- marketing consent is enforced
- merge is transactional and audited
- soft deletion preserves historical records
- list and profile permissions are enforced server-side
- sensitive notes are protected
- dummy customer data is isolated from production

## 5. LEADS MODULE

### 5.1 Purpose

The Leads module manages corporate catering, group dining, event enquiries, partnership enquiries, recurring office orders, customer referrals, and other commercial opportunities before they become customers or confirmed orders.

### 5.2 Lead types

- corporate_catering
- recurring_office_order
- event_booking
- group_dining
- partnership
- franchise_or_business_enquiry
- general_sales_enquiry

The system may display friendly labels while storing stable machine-safe values.

### 5.3 Lead sources

- website
- phone
- walk_in
- whatsapp
- zomato_import
- swiggy_import
- meta_campaign
- google_campaign
- referral
- corporate_outreach
- event_enquiry
- offline_qr

### 5.4 Lead statuses

- new
- contacted
- qualified
- interested
- follow_up_scheduled
- proposal_shared
- negotiating
- won
- lost
- closed

### 5.5 Lead list page

Columns:

- lead number
- display name
- organization
- lead type
- source
- status
- priority
- estimated value
- requested date
- party size
- assigned staff
- next follow-up
- last activity
- created time

### 5.6 Lead pipeline board

Kanban columns use approved statuses.

Requirements:

- server-backed pagination by stage
- drag-and-drop only when transition is valid
- transition confirmation when required
- reason required for lost or closed
- optimistic UI with rollback on failure
- card counts and estimated value totals
- no loading of the complete lead database at once

### 5.7 Lead detail page

Header:

- lead number
- display name
- organization
- status
- priority
- estimated value
- assigned staff
- next follow-up

Tabs:

- Overview
- Activity
- Follow-ups
- Communications
- Attachments
- Conversion
- Audit

### 5.8 Lead qualification fields

- lead type
- contact person
- organization
- phone
- email
- requested date and time
- party size
- estimated value
- food preferences
- service requirements
- delivery or venue requirements
- budget notes
- frequency for recurring orders
- decision deadline
- source
- campaign
- assigned staff
- qualification notes

### 5.9 Lead activities

Activity types:

- call
- email
- WhatsApp
- meeting
- proposal
- note
- status change
- assignment
- follow-up created
- follow-up completed
- file added
- customer conversion
- order conversion

### 5.10 Follow-ups

A follow-up includes:

- scheduled time
- assigned staff
- purpose
- channel
- status
- outcome
- next action

Statuses:

- scheduled
- due
- completed
- cancelled
- missed

Overdue follow-ups must appear on the dashboard and lead module.

### 5.11 Lead conversion

A lead may convert into:

- customer
- reservation request
- assisted order
- corporate customer and recurring-order arrangement

Conversion workflow:

1. Validate contact data.
2. Check customer duplicates.
3. Select existing or create customer.
4. Create linked downstream record if requested.
5. Mark lead won.
6. Store conversion references.
7. Preserve lead history.
8. Audit the action.

### 5.12 Lost lead workflow

Required:

- lost reason
- optional competitor
- notes
- future re-engagement date when appropriate

Example reasons:

- budget
- timing
- no_response
- chose_competitor
- service_unavailable
- location_issue
- menu_mismatch
- duplicate
- invalid_enquiry

### 5.13 Lead AI support

Allowed advisory features (available only from Phase 14 onward, once AI is credentialed):

- summarize activity
- suggest next best action
- identify overdue risk
- prioritize leads using explainable factors
- draft follow-up messages
- identify missing qualification information

AI must not change status, send messages, adjust values, or convert records without explicit user action.

### 5.14 Lead reporting

- leads by source
- leads by type
- pipeline value
- conversion rate
- average time to first contact
- average sales-cycle duration
- won and lost reasons
- overdue follow-ups
- performance by assigned staff

### 5.15 Lead edge cases

- duplicate lead from multiple channels
- lead already linked to customer
- event date in the past
- missing contact method
- estimated value changed during negotiation
- lead owner disabled
- follow-up overdue during staff leave
- lost lead reopened
- converted lead with later cancellation

### 5.16 Lead acceptance criteria

- all transitions are validated by backend
- lost reasons are required
- overdue follow-ups are accurate
- conversion is transactional
- duplicate customer checking occurs
- board movements cannot bypass permissions
- activity history is preserved
- AI recommendations remain advisory

## 6. ORDERS & RESTAURANT OPERATIONS MODULE

### 6.1 Purpose

This module controls the full lifecycle of dine-in, takeaway, delivery, website, assisted, corporate, event, imported aggregator, and POS orders.

It is the most operationally sensitive module because it affects revenue, payments, stock, kitchen workload, fulfilment, customer history, loyalty, refunds, and reports.

### 6.2 Supported order sources

- website
- mobile_web
- whatsapp_assisted
- phone_assisted
- pos_import
- zomato_import
- swiggy_import
- corporate
- event

### 6.3 Supported order types

- dine_in
- takeaway
- delivery
- corporate_delivery
- event_catering

### 6.4 Order statuses

- draft
- pending_payment
- payment_verification_pending
- confirmed
- accepted
- preparing
- quality_check
- ready
- picked_up
- out_for_delivery
- delivered
- cancelled
- refund_requested
- refund_processing
- refunded
- failed

Payment and fulfilment statuses remain separate so that operational and financial state are not overloaded into one field.

### 6.5 Order list page

Columns:

- order number
- source
- order type
- customer
- status
- payment status
- fulfilment status
- item count
- total
- assigned staff
- created time
- time in current status
- external-order indicator

### 6.6 Order filters

- date range
- source
- order type
- status
- payment status
- fulfilment status
- customer
- assigned staff
- total range
- contains product
- refund state
- delayed state
- external order state

### 6.7 Operational queue views

- Awaiting payment
- Awaiting verification
- New confirmed orders
- Awaiting acceptance
- Preparing
- Quality check
- Ready
- Pickup queue
- Delivery queue
- Delayed
- Cancellation review
- Refund review
- Failed imports

Each queue must use bounded server queries.

### 6.8 Order creation

Order creation steps:

1. Select or create customer where applicable.
2. Select source and order type.
3. Add products and variants.
4. Add modifiers.
5. Add item instructions.
6. Validate availability.
7. Enter delivery, table, pickup, corporate, or event details.
8. Apply eligible discount or loyalty redemption.
9. Review backend-calculated totals.
10. Select payment workflow.
11. Confirm order.

Client-provided totals are never authoritative.

### 6.9 Order item presentation

Each line displays:

- product snapshot
- variant snapshot
- modifiers
- quantity
- unit price
- line discount
- line tax
- line total
- special instructions
- availability warning

### 6.10 RKPR dummy menu references

The order interface must use the exact development menu from `PROJECT_PLAN.md`, including:

- RKPR Classic Veg Burger — ₹179
- RKPR Spicy Paneer Burger — ₹229
- Smoky BBQ Chicken Burger — ₹259
- Double Crunch Chicken Burger — ₹299
- Jain Aloo Crunch Burger — ₹189
- Margherita Pizza variants
- Farmhouse Veg Pizza variants
- Paneer Tikka Pizza variants
- BBQ Chicken Pizza variants
- Mexican Fire Pizza variants
- approved tacos, burritos, bowls, sides, beverages, desserts, combos, and add-ons

Approved dummy modifiers include:

- Cheese slice — ₹35
- Extra paneer patty — ₹80
- Extra chicken patty — ₹100
- Extra vegetable patty — ₹60
- Jalapeños — ₹25
- Extra sauce — ₹20
- Gluten-aware bun substitute — ₹60
- Make it Jain — no charge where possible
- Make it extra spicy — no charge
- Remove ingredient — no charge

These are seed values, not hardcoded UI constants.

### 6.11 Price and total calculation

Backend calculation order must be explicitly defined and tested. All amounts are integer minor units.

Typical components:

- item subtotal
- modifier subtotal
- line discounts
- order discount
- loyalty discount
- taxable base
- tax
- packaging
- delivery
- final total

The UI must show a transparent breakdown.

### 6.12 Discount handling

Discount types may include:

- fixed amount
- percentage
- product-specific
- category-specific
- coupon
- customer-service recovery
- staff-authorized manual discount
- loyalty redemption

Requirements:

- eligibility checked by backend
- authorization thresholds (`orders.discount.apply`)
- reason for manual discount
- no negative payable amount
- historical discount snapshot
- audit log for sensitive adjustments

### 6.13 Payment handling

Payment statuses may include:

- unpaid
- pending
- verification_pending
- authorized
- paid
- partially_paid
- failed
- refund_pending
- partially_refunded
- refunded

Supported methods depend on confirmed integrations. The UI must never claim a provider or method is connected unless connection verification succeeds.

### 6.14 Payment verification

- Provider webhooks are authoritative for provider-confirmed payments.
- Duplicate events are idempotent.
- Manual verification requires permission, evidence, reason, and audit.
- Failed payment must not create duplicate orders when retried with the same idempotency key.

### 6.15 Refund workflow

1. Create refund request (`orders.refund.request`).
2. Select full or partial refund.
3. Enter amount and reason.
4. Validate refundable balance.
5. Require approval where configured (`orders.refund.approve`).
6. Submit provider refund or manual workflow.
7. Track provider events.
8. Update payment and order status.
9. Reverse loyalty effects where applicable.
10. Audit every step.

### 6.16 Cancellation workflow

Cancellation must consider:

- current order status
- payment state
- inventory reservation
- kitchen preparation state
- delivery assignment
- refund requirement
- loyalty effects
- customer notification

A cancelled order must release unconsumed inventory reservations transactionally.

### 6.17 Kitchen workflow

Kitchen-facing data:

- order number
- channel
- order type
- elapsed time
- item list
- variants
- modifiers
- dietary flags
- special instructions
- priority
- promised time

Kitchen status flow:

- accepted
- preparing
- quality_check
- ready

The kitchen view must not expose unnecessary customer financial or personal information.

### 6.18 Preparation targets

Product or category preparation targets may be configured. The system should calculate:

- time waiting for acceptance
- preparation time
- time in quality check
- time ready before pickup
- delivery handoff time

Delayed orders must be visually prioritized.

### 6.19 Inventory integration

At the configured lifecycle state, the system must:

- validate recipe availability
- reserve required ingredients
- consume inventory when preparation reaches the defined state
- release unused reservations on cancellation
- create append-only stock movements
- avoid duplicate consumption

Manual stock changes are not allowed through order screens.

### 6.20 Menu availability integration

When required ingredients are unavailable:

- affected products can become unavailable through derived availability
- users must see why an item is unavailable where permitted
- authorized staff may create time-limited manual overrides
- overrides require reason and expiry

### 6.21 Order detail page

Sections:

- order summary
- customer
- source and fulfilment
- items
- price breakdown
- payment
- kitchen timeline
- fulfilment timeline
- inventory reservations
- communications
- notes
- refund and cancellation
- audit history

### 6.22 Order timeline

Events include:

- created
- payment initiated
- payment verified
- confirmed
- accepted
- preparing
- quality check
- ready
- picked up
- out for delivery
- delivered
- cancelled
- refund requested
- refund processed
- failed

### 6.23 Dine-in workflow

Must support:

- table assignment
- guest count
- linked reservation
- course or firing notes where later approved
- additional items before bill closure
- assisted payment workflow

Split-bill and merge-bill behavior must not be implemented unless fully designed in the approved scope. The system must not invent partial functionality.

### 6.24 Delivery workflow

Must support:

- address
- delivery instructions
- delivery zone validation
- delivery charge
- promised time
- delivery assignment reference
- out-for-delivery state
- delivered state
- failed-delivery reason

### 6.25 Imported orders

For POS, Zomato, and Swiggy imports:

- preserve external order ID
- map external products to internal products where possible
- flag unmapped items
- deduplicate provider events
- show source badge
- track sync errors
- never fabricate data unavailable from provider payloads

### 6.26 Corporate and event orders

Additional fields:

- organization
- contact person
- event or delivery date
- service time
- headcount
- billing notes
- purchase order reference
- linked lead
- linked customer
- special menu
- approval state

### 6.27 Order bulk actions

Limited actions:

- assign staff
- export
- print operational tickets
- mark selected eligible orders as accepted only if transition rules permit

Bulk cancellation, bulk refund, and bulk financial adjustment are not ordinary actions.

### 6.28 Order edge cases

- price changes after draft creation
- item becomes unavailable before confirmation
- payment succeeds after timeout
- duplicate webhook
- order imported twice
- order cancelled during preparation
- partial refund
- refund after loyalty award
- customer merge involving active order
- stock shortage after reservation
- external item not mapped
- delivery failure
- stale status update from two staff users

### 6.29 Order acceptance criteria

- all totals reconcile with backend
- all status transitions are explicit
- payment events are idempotent
- stock reservations and consumption are transactional
- historical snapshots remain stable
- delayed queues are accurate
- imported orders deduplicate correctly
- kitchen views minimize personal data
- refund and cancellation effects reconcile with loyalty and reports

## 7. MENU & PRODUCTS MODULE

### 7.1 Purpose

The Menu & Products module controls what RKPR sells, how items are grouped, priced, described, modified, prepared, costed, and made available across channels.

### 7.2 Menu categories

Seed categories:

- Burgers
- Pizzas
- Tacos
- Burritos and Bowls
- Sides
- Beverages
- Desserts
- Combos

Category fields:

- code
- name
- description
- sort order
- active state
- channel visibility
- service-time visibility where approved

### 7.3 Product list

Columns:

- product code
- name
- category
- food type
- base price
- variant count
- estimated food cost
- margin
- active state
- current availability
- availability source
- preparation time
- updated time

### 7.4 Product detail

Tabs:

- General
- Pricing
- Variants
- Modifiers
- Recipe
- Availability
- Nutrition and allergens
- Channels
- Sales analytics
- Audit

### 7.5 Product fields

- product code
- name
- slug
- category
- description
- food type
- Jain capable
- vegan capable
- preparation minutes
- calories
- base price
- tax category
- image
- active state
- availability state
- availability source
- override expiry
- override reason

### 7.6 Variants

Use variants where the item is fundamentally the same product with a selectable size or configuration.

Examples:

- 8-inch pizza
- 11-inch pizza

Variant fields:

- code
- name
- price
- active state
- sort order
- recipe override if required

### 7.7 Modifier groups

Examples:

- Add-ons
- Patty selection
- Sauce selection
- Spice level
- Remove ingredients
- Dietary preparation

Rules:

- minimum selections
- maximum selections
- required or optional
- per-product mapping
- availability
- sort order
- channel-specific support only when approved

### 7.8 Product availability

Sources:

- manual
- inventory_derived
- schedule
- integration
- override

The final displayed state must include a clear reason internally.

Manual override requirements:

- authorized user
- reason
- start time
- expiry time
- audit log

### 7.9 Recipes

A recipe links a product or variant to inventory ingredients and quantities.

Recipe requirements:

- versioned
- effective dates
- quantity required
- waste factor
- unit compatibility
- cost calculation
- no silent retroactive change to historical orders

### 7.10 Cost and margin

Product cost may include:

- recipe ingredient cost
- packaging cost
- optional estimated channel cost

Display:

- estimated food cost
- gross margin amount
- gross margin percentage
- cost trend

Cost values are operational estimates and must state their calculation basis.

### 7.11 Menu images

- stored privately or in approved public asset delivery path
- validated file type and size
- optimized derivatives
- alt text
- focal point where needed
- no base64 storage in database

### 7.12 Nutrition and allergen data

Fields may include:

- calories
- vegetarian/non-vegetarian
- vegan capable
- Jain capable
- contains dairy
- contains gluten
- contains nuts
- contains soy
- contains egg

Allergen labels must not claim guaranteed allergen-free preparation unless independently verified and operationally supported.

### 7.13 Menu search and filters

- name
- code
- category
- food type
- active
- available
- variant state
- margin range
- missing recipe
- missing image
- missing tax category

### 7.14 Menu bulk actions

- activate
- deactivate
- set category
- set availability
- export
- channel visibility update when approved

Bulk price changes require preview, permission, effective time, and audit.

### 7.15 Menu analytics

- units sold
- revenue
- discount impact
- refund rate
- cancellation rate
- estimated food cost
- gross margin
- channel mix
- repeat-customer preference

### 7.16 Menu edge cases

- product without recipe
- inactive category with active products
- variant price below zero
- modifier mapped to unavailable ingredient
- image upload failure
- scheduled availability conflict
- manual override expiration
- product used in historical order
- ingredient unit mismatch

### 7.17 Menu acceptance criteria

- seed data matches `PROJECT_PLAN.md`
- prices are data-driven
- variants and modifiers validate correctly
- recipe versions are preserved
- availability state has an explainable source
- historical orders remain unchanged
- bulk changes are audited

## 8. INVENTORY & SUPPLIERS MODULE

### 8.1 Purpose

This module controls ingredients, packaging, beverages, desserts, stock levels, batches, expiry, purchasing, receiving, waste, adjustments, recipe consumption, suppliers, and inventory risk.

### 8.2 Inventory item list

Columns:

- item code
- name
- category
- storage zone
- unit
- current stock
- reserved stock
- available stock
- reorder level
- target stock
- stock status
- preferred supplier
- average unit cost
- next expiry
- last counted

### 8.3 Stock statuses

- in_stock
- low_stock
- critical_stock
- out_of_stock
- reserved
- quarantined
- expired
- damaged
- under_count_review
- discontinued

### 8.4 Inventory item profile

Tabs:

- Overview
- Stock movements
- Batches
- Suppliers
- Purchase history
- Recipe usage
- Counts
- Alerts
- Audit

### 8.5 Inventory item fields

- item code
- name
- category
- storage zone
- unit of measure
- current stock
- reserved stock
- reorder level
- target stock
- maximum stock
- average unit cost
- preferred supplier
- alternative supplier
- lead time
- shelf life
- batch tracking
- expiry tracking
- allergen flags
- status
- last counted
- last received

### 8.6 Dummy inventory consistency

Seed inventory must match `PROJECT_PLAN.md`, including the same stock values, reorder levels, costs, and units for:

- burger buns
- vegetable patties
- paneer patties or paneer stock
- chicken patties or chicken stock
- mozzarella
- cheddar
- pizza bases or dough ingredients
- fries
- taco shells
- tortillas
- vegetables
- sauces
- beverages
- desserts
- packaging

No later document may create conflicting seed values.

### 8.7 Stock movement types

- purchase_receipt
- kitchen_issue
- recipe_consumption
- adjustment
- waste
- damage
- expiry
- supplier_return
- transfer
- count_correction
- reservation
- release

Every movement is append-only and includes quantity, unit cost where relevant, reference, reason, actor, and timestamp.

### 8.8 Receiving workflow

1. Select purchase order or supplier.
2. Enter invoice and receipt reference.
3. Add received quantities.
4. Record batch codes.
5. Record manufacture and expiry dates.
6. Record unit cost.
7. Record damaged or rejected quantity.
8. Validate unit conversion.
9. Preview stock effect.
10. Confirm transaction.

Confirmation creates goods receipt, batches, stock movements, cost updates, and audit events in one controlled operation.

### 8.9 Stock adjustment workflow

Required:

- item
- quantity change
- reason
- evidence or note for sensitive adjustments
- expected version
- approval when configured

Adjustment reasons:

- count_difference
- data_correction
- damaged
- spoiled
- missing
- found
- unit_conversion_correction

### 8.10 Waste workflow

Capture:

- item
- batch
- quantity
- reason
- station
- linked order where applicable
- actor
- timestamp
- optional photo evidence

Waste reasons:

- preparation_waste
- overproduction
- spoilage
- expiry
- customer_return
- quality_failure
- accidental_damage

### 8.11 Cycle counts

Cycle-count process:

1. Create count session.
2. Freeze or snapshot expected stock.
3. Assign counters.
4. Record physical quantities.
5. Review variance.
6. Approve corrections.
7. Create count-correction movements.
8. Close session.

Large variances require escalation.

### 8.12 Batch and expiry management

Batch fields:

- batch code
- supplier
- received quantity
- remaining quantity
- received date
- manufacture date
- expiry date
- status
- unit cost

Expiry views:

- expires within 3 days
- expires within 7 days
- expires within 14 days
- expired

FIFO or FEFO guidance may be displayed, but consumption accounting must follow the approved implementation strategy.

### 8.13 Supplier list

Seed suppliers must match `PROJECT_PLAN.md`:

- Bengaluru Bakers Supply
- Nandi Dairy Foods
- Southern Poultry Co.
- GreenLeaf Produce
- FrostBite Distributors
- MexiSource India
- TasteCraft Condiments
- EcoPack Bengaluru

Supplier fields:

- supplier code
- name
- contact person
- phone
- email
- address
- supply categories
- lead time
- payment terms
- minimum order value
- status

### 8.14 Supplier detail

Tabs:

- Overview
- Supplied items
- Purchase orders
- Receipts
- Returns
- Performance
- Communications
- Documents
- Audit

### 8.15 Purchase orders

Statuses:

- draft
- submitted
- acknowledged
- partially_received
- received
- cancelled
- closed

Purchase order fields:

- PO number
- supplier
- order date
- expected delivery
- items
- quantities
- unit costs
- taxes
- total
- notes
- approval state

### 8.16 Supplier performance

Metrics:

- on-time delivery rate
- fill rate
- rejection rate
- average lead time
- price variance
- quality incidents
- return count

Metrics must state the measured period.

### 8.17 Inventory alerts

Alert types:

- low stock
- critical stock
- out of stock
- expiring soon
- expired
- quarantined
- overdue count
- unusual consumption
- purchase order overdue

Alerts should be deduplicated and resolved when the condition clears.

### 8.18 Inventory valuation

Display:

- current inventory value
- value by category
- value by storage zone
- waste value
- expiry value
- purchase variance

The valuation method must be explicitly configured and consistently applied.

### 8.19 Inventory permissions

Sensitive actions, all requiring explicit permission from the canonical registry (`inventory.adjust`, `inventory.receive`, `inventory.transfer`, and related):

- adjustment
- receipt confirmation
- waste approval
- count correction
- supplier change
- cost change
- purchase order approval

### 8.20 Inventory edge cases

- negative stock attempt
- duplicate receipt
- batch expires before receipt date
- supplier item unit mismatch
- simultaneous adjustment
- order cancellation after consumption
- product recipe changed mid-day
- quarantined batch
- partial PO receipt
- expired ingredient still reserved

### 8.21 Inventory acceptance criteria

- all stock changes have ledger entries
- current stock reconciles with movement history
- reservations do not duplicate
- batch expiry is enforced where configured
- receiving is transactional
- seed data matches prior documents
- supplier metrics use real purchase data
- negative stock behavior follows explicit policy

## 9. RESERVATIONS & CALENDAR MODULE

### 9.1 Purpose

This module manages reservation requests, human review, table capacity, seating zones, reminders, arrivals, seating, completion, cancellation, and no-shows.

The initial system does not automatically approve reservations.

### 9.2 Reservation statuses

- requested
- pending_review
- needs_clarification
- approved
- rejected
- confirmation_sending
- confirmed
- reminder_scheduled
- arrived
- seated
- completed
- no_show
- cancelled_by_customer
- cancelled_by_restaurant

### 9.3 Reservation list page

Columns:

- reservation number
- guest name
- phone
- date
- start time
- guest count
- seating zone
- status
- approval state
- assigned staff
- special-request indicator
- created source

### 9.4 Calendar views

- Day
- Week
- Month
- Agenda

Day and week views show capacity and table assignments. Month view summarizes counts and covers without rendering excessive details.

### 9.5 Reservation request creation

Fields:

- existing customer or guest
- guest name
- phone
- email
- date
- start time
- estimated end time
- guest count
- preferred seating zone
- special requests
- occasion
- source
- assigned staff

### 9.6 Review workflow

1. Open pending request.
2. Validate operating hours.
3. Review guest count.
4. Review capacity.
5. Review conflicting table assignments.
6. Review special requests.
7. Request clarification, approve, or reject.
8. Assign tables if appropriate.
9. Send confirmation asynchronously.
10. Schedule reminders.

### 9.7 Approval rules

Approval (`reservations.approve`) must check:

- restaurant is open
- requested time is valid
- guest count is positive
- seating capacity exists
- table conflicts are resolved
- large-group policy
- special request feasibility
- customer no-show or complaint context when permitted

Approval remains a human action.

### 9.8 Table configuration

Table fields:

- table code
- seating zone
- capacity
- accessibility
- active state
- merge group

The module must support combining compatible tables only through explicit assignment rules.

### 9.9 Capacity view

Display by time slot:

- total capacity
- approved covers
- pending covers
- remaining capacity
- table conflicts
- accessible-table availability

Pending requests must not be silently treated as approved capacity.

### 9.10 Reservation detail page

Sections:

- guest and contact details
- date and time
- guest count
- seating preference
- table assignments
- special requests
- occasion
- status timeline
- reminders
- communications
- linked customer
- linked order
- notes
- audit

### 9.11 Confirmation and reminders

Confirmation and reminder sending is asynchronous (ARQ worker).

Track:

- scheduled
- queued
- sent
- delivered
- failed
- cancelled
- retrying

Failed communication does not reverse reservation approval, but it must create an actionable alert.

### 9.12 Arrival and seating

Flow:

- confirmed to arrived
- arrived to seated
- seated to completed

The UI must show waiting time after arrival and seating duration.

### 9.13 No-show workflow

Requirements:

- mark no-show only after configured grace period
- require user confirmation
- record reason or note
- update customer metrics
- preserve communication attempts

### 9.14 Cancellation workflow

Capture:

- cancellation source
- reason
- timestamp
- actor
- deposit or payment implication if later implemented
- customer notification state

### 9.15 Waitlist

Waitlist may be included only if approved in the final phase scope. When implemented, it must include:

- requested date and time
- acceptable time range
- guest count
- contact details
- status
- priority order
- offer expiry

It must not be simulated without complete backend support.

### 9.16 Group and event reservations

Additional fields:

- organization
- lead link
- event type
- estimated spend
- menu requirement
- deposit requirement if approved
- event notes
- responsible staff

### 9.17 Reservation search and filters

- date range
- status
- approval state
- guest name
- phone
- customer
- guest-count range
- seating zone
- assigned staff
- source
- special request
- no-show history

### 9.18 Reservation bulk actions

Limited actions:

- assign staff
- export
- send approved reminder batch through a controlled job

Bulk approval is not allowed in the initial system.

### 9.19 Reservation edge cases

- duplicate request
- invalid time
- request outside hours
- table conflict
- guest count exceeds capacity
- reservation edited after confirmation
- communication failure
- customer arrives early
- customer arrives late
- no-show later disputes status
- merged customer records
- disabled assigned staff

### 9.20 Reservation acceptance criteria

- no automatic approval
- capacity checks are authoritative
- table conflicts are prevented
- reminders are durable and retryable
- all transitions are logged
- no-show handling follows grace period
- list and calendar remain fast with large data volume
- confirmation failure is visible

## 10. CROSS-MODULE WORKFLOWS

### 10.1 Lead to customer to order

- lead qualified
- customer duplicate check
- customer created or selected
- order created
- lead marked won
- references preserved
- activity and audit events created

### 10.2 Lead to reservation

- lead qualified
- customer selected or created
- reservation request created
- human approval remains required
- lead conversion reference stored

### 10.3 Reservation to dine-in order

- reservation approved
- guest arrives
- guest seated
- dine-in order linked
- customer activity timeline updated

### 10.4 Order to inventory

- order confirmed or accepted according to configured point
- stock reserved
- preparation begins
- stock consumed
- cancellation releases remaining reservation
- stock movement history preserved

### 10.5 Order to loyalty

- eligible completed direct order
- points awarded idempotently
- refund reverses eligible points
- customer balance and ledger reconcile

### 10.6 Complaint recovery

- complaint linked to customer and order or reservation
- recovery action approved
- discount, refund, or loyalty adjustment performed through authorized workflow
- customer segment may become complaint_recovery
- all effects audited

## 11. MODULE NOTIFICATION MATRIX

Examples:

- New high-value lead → assigned salesperson and manager
- Overdue follow-up → assigned salesperson
- New confirmed order → operations queue
- Delayed order → shift supervisor and operations manager
- Refund request → finance or authorized approver
- Critical stock → inventory manager and kitchen manager
- Expiring batch → inventory manager
- Pending reservation review → reservation team
- Reservation communication failure → reservation manager
- High-severity complaint → general manager

Notifications must be deduplicated, permission-aware, and link to the exact record.

## 12. MODULE REPORTING MATRIX

Dashboard:

- executive summary
- daily operations snapshot

Customers:

- customer growth
- retention
- segment distribution
- lifetime value

Leads:

- pipeline
- conversion
- source performance
- follow-up performance

Orders:

- sales
- channel mix
- preparation time
- cancellations
- refunds

Menu:

- product performance
- margin
- modifier usage

Inventory:

- stock status
- consumption
- waste
- expiry
- purchase variance

Reservations:

- covers
- utilization
- no-show rate
- cancellation rate

## 13. MODULE PERFORMANCE TARGETS

- Initial useful content should render without waiting for secondary panels.
- List endpoints return bounded responses.
- Common filter queries must be index-supported.
- Detail pages fetch summary first and lazy-load secondary tabs.
- Timeline feeds use cursor pagination.
- Export and report generation must never run synchronously in a page request for large ranges — use the ARQ worker.
- Realtime subscriptions must remain scoped to visible operational data.
- Failed provider calls must not block ordinary CRM navigation.

## 14. MODULE SECURITY TARGETS

- Every action maps to an explicit permission from the canonical capability registry.
- Sensitive fields are excluded by default.
- Financial and inventory adjustments require reason and audit.
- Customer consent is checked at action time.
- Customer merge is privileged and transactional.
- Reservation approval is permission-controlled.
- Files are private and scanned.
- External IDs and webhook events are deduplicated.
- No module exposes secrets or provider payloads.

## 15. CORE MODULE DEFINITION OF DONE

A core module is complete only when:

- product behavior matches this document
- database and API behavior matches `DATABASE_AND_API.md`
- dummy data matches `PROJECT_PLAN.md`
- architecture matches `ARCHITECTURE_AND_TECH_STACK.md`
- security and coding rules match `CLAUDE.md`
- all list screens are paginated
- permissions are tested
- loading, empty, error, stale-data, and conflict states exist
- state transitions are validated
- sensitive actions are audited
- primary workflows have automated tests
- cross-module effects reconcile
- accessibility requirements are met
- mobile and tablet behavior is usable
- no incomplete fake integration or placeholder workflow is shown as functional

## 16. FINAL CORE MODULE COMMAND

Build the RKPR core CRM modules as operational software, not static dashboard screens. Every module must be fast, data-rich, permission-aware, transaction-safe, auditable, and consistent with the approved business rules. Preserve exact dummy seed data only for development and testing. Never substitute dummy information for architecture, provider behavior, security, financial logic, inventory logic, API contracts, or production decisions.
