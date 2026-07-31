# RKPR RESTAURANT CRM — GROWTH AND INTELLIGENCE

## 1. DOCUMENT PURPOSE

This document defines the complete product behavior, operational rules, data presentation, permissions, automation boundaries, analytical definitions, reporting logic, controlled AI capabilities, validation, failure handling, and acceptance criteria for the RKPR Restaurant CRM growth and intelligence modules.

It must remain consistent with `PROJECT_PLAN.md`, `ARCHITECTURE_AND_TECH_STACK.md`, `DATABASE_AND_API.md`, `CORE_CRM_MODULES.md`, and `OPERATIONS_MODULES.md`.

The modules covered are:

1. Marketing and Campaign Management
2. Customer Segmentation and Audience Management
3. Loyalty and Rewards
4. Offers, Coupons, and Promotions
5. Feedback and Reviews
6. Complaints and Service Recovery Intelligence
7. Reports and Analytics
8. Controlled AI Center
9. Forecasting and Decision Support
10. Growth Operations and Cross-Module Workflows

This document is product-authoritative for how the CRM supports customer growth, retention, loyalty, service recovery, management reporting, and advisory intelligence.

Dummy information is permitted only for development fixtures such as sample campaigns, sample customer segments, loyalty balances, coupon codes, feedback records, complaint examples, and dashboard values. Important matters such as architecture, technology providers, security, formulas, permissions, legal compliance, financial logic, AI behavior, deployment, and production decisions must never use dummy assumptions.

The Controlled AI Center (§14) is implemented and credentialed only in Phase 14 — Reports, Analytics, and Controlled AI, per `ROADMAP.md`. Every AI feature described in this document is advisory-only and inactive until that phase.

## 2. GROWTH AND INTELLIGENCE PRINCIPLES

### 2.1 Restaurant-specific scope

The system is not a generic marketing automation platform, data warehouse, business intelligence SaaS, or autonomous AI agent.

Every growth feature must directly support the RKPR restaurant's actual workflows:

- repeat visits
- order frequency
- average order value
- corporate and group enquiries
- reservation conversion
- loyalty engagement
- product and category performance
- campaign effectiveness
- customer satisfaction
- complaint prevention
- service recovery
- staff and operational decision support

### 2.2 Source-of-truth rules

- PostgreSQL remains the authoritative source for CRM records.
- Reports must use defined transactional and aggregated data models.
- Redis may cache bounded analytical responses but cannot become the system of record.
- Customer consent must be evaluated from current CRM consent records at execution time.
- Loyalty balances must derive from an immutable ledger, not an editable total alone.
- Discounts and promotions must retain rule evaluation and financial history.
- AI output must be grounded in accessible CRM data and must never create factual records silently.
- Dashboard values must expose their reporting window and freshness.
- All money values use integer minor units in storage and INR display conventions established in `DATABASE_AND_API.md` §3.3.
- All business timestamps use `Asia/Kolkata` for display while storage follows the approved database standard.

### 2.3 Data quality before intelligence

No analytical or AI feature may hide poor data quality.

The system must detect and surface:

- missing customer identity
- duplicate customers
- missing consent source
- incomplete order attribution
- cancelled or refunded order inclusion errors
- missing product cost data
- missing campaign attribution
- unresolved complaint linkage
- stale segment membership
- failed report refresh
- incomplete loyalty ledger reconciliation

Where input quality is insufficient, the system must show a clear limitation rather than a confident but misleading result.

### 2.4 Human control

The following always require human authorization:

- publishing a campaign
- sending marketing communication
- changing loyalty rules
- issuing discretionary loyalty adjustments
- approving high-value discounts
- approving refunds or service recovery compensation
- publishing pricing or policy changes
- accepting an AI-generated customer-facing message
- applying AI recommendations to customer, staff, financial, or operational records

## 3. MARKETING AND CAMPAIGN MANAGEMENT

### 3.1 Purpose

The Marketing module allows authorized users to plan, approve, schedule, execute, monitor, and evaluate restaurant-specific customer campaigns.

It supports controlled communication to eligible customer audiences. It does not permit unrestricted bulk messaging.

### 3.2 Campaign types

Approved campaign type values:

- promotional_offer
- product_launch
- seasonal_menu
- festival
- loyalty_engagement
- win_back
- birthday
- anniversary
- reservation_drive
- corporate_outreach
- feedback_request
- event_invitation
- service_announcement
- operational_notice

Operational notices must remain distinct from marketing communication and use the correct communication basis.

### 3.3 Campaign statuses

- draft
- in_review
- approved
- scheduled
- running
- paused
- completed
- cancelled
- failed
- archived

Allowed high-level transition flow:

`draft -> in_review -> approved -> scheduled -> running -> completed`

Alternative controlled transitions:

- `in_review -> draft` when changes are requested
- `approved -> cancelled`
- `scheduled -> paused`
- `paused -> scheduled` or `paused -> cancelled`
- `running -> paused` where the channel supports stopping future sends
- `running -> failed` on unrecoverable execution failure
- terminal campaigns may later become `archived`

A campaign cannot become `approved` without an authorized reviewer holding `campaigns.approve`.

### 3.4 Campaign fields

Required or supported fields:

- campaign number
- internal name
- public title where applicable
- type
- objective
- description
- status
- owner
- reviewer
- approved by
- target audience definition
- channel set
- message template version
- offer or coupon linkage
- landing or destination reference where applicable
- planned start time
- planned end time
- send window
- timezone
- frequency cap
- suppression rules
- estimated audience size
- actual eligible audience size
- control group configuration where approved
- budget where tracked
- attribution window
- tags
- created by
- created time
- updated by
- updated time
- approved time
- execution summary

### 3.5 Campaign channels

Provider-neutral channel values:

- whatsapp
- email
- sms
- website_banner
- in_app
- manual_outreach

A channel may be selected only when the corresponding integration or manual workflow is implemented and active.

No screen may falsely present an unavailable channel as operational.

### 3.6 Campaign list page

Columns:

- campaign number
- name
- type
- status
- owner
- audience
- channels
- scheduled time
- eligible recipients
- sent
- delivered
- conversion count
- attributed revenue
- updated time

Default saved views:

- Drafts
- Awaiting review
- Approved
- Scheduled
- Running
- Completed recently
- Failed
- My campaigns
- Campaigns with offer
- Corporate outreach

### 3.7 Campaign detail page

Sections:

- campaign summary
- objective and success metric
- ownership and approval
- audience definition
- consent and suppression summary
- channel configuration
- content and template preview
- linked offer or coupon
- schedule
- execution progress
- delivery metrics
- engagement metrics where supported
- conversion and revenue attribution
- failure and retry summary
- activity timeline
- audit history

Primary actions depend on status and permission:

- Edit
- Submit for review
- Approve
- Request changes
- Schedule
- Pause
- Resume
- Cancel
- Duplicate as draft
- Archive
- Export performance report

### 3.8 Campaign creation workflow

1. Authorized user creates a draft.
2. User selects campaign type and objective.
3. User selects or creates an audience definition.
4. System estimates audience size.
5. User selects channels.
6. User selects approved templates or creates draft content.
7. User links an offer or coupon where relevant.
8. System validates consent, suppressions, channel availability, template variables, schedule, and frequency limits.
9. User previews representative messages.
10. User submits for review.
11. Reviewer approves or requests changes.
12. Approved campaign is scheduled.
13. At execution time, the eligible audience is recalculated.
14. Recipient-level send jobs are created idempotently (ARQ worker).
15. Delivery and conversion events are recorded.
16. Campaign completes when all terminal recipient states are reached or the configured end condition occurs.

### 3.9 Campaign approval rules

Approval must consider:

- correct campaign classification
- valid consent basis
- accurate offer terms
- approved pricing
- approved message content
- correct audience
- frequency cap compliance
- exclusions and suppressions
- schedule and expiry
- financial impact
- operational capacity
- inventory availability where the campaign promotes limited products

The system must preserve the exact approved campaign version. Later edits must return the campaign to a review-required state unless they are explicitly non-substantive metadata changes.

### 3.10 Recipient eligibility

A recipient is eligible only when all relevant conditions pass:

- customer record is active and usable
- required contact value exists
- contact value is valid for the selected channel
- current consent permits the communication
- customer is not suppressed
- customer belongs to the resolved audience
- customer has not exceeded frequency cap
- customer has not already received the same idempotent campaign execution
- campaign, template, offer, and channel are active
- send time is within the allowed window

Eligibility must be calculated at send time, not frozen only at campaign creation.

### 3.11 Suppression rules

Suppression may result from:

- withdrawn marketing consent
- channel opt-out
- invalid or bounced email
- invalid phone
- permanent provider failure
- customer-deceased or do-not-contact administrative state where supported
- complaint-related temporary suppression
- active service recovery hold
- internal test account
- employee account where excluded
- recent campaign frequency cap
- explicit campaign exclusion segment

Suppression reason must be retained for reporting without exposing sensitive details to unauthorized users.

### 3.12 Frequency controls

Frequency rules may include:

- maximum marketing messages per channel per rolling period
- minimum time between campaigns
- campaign-specific one-time delivery
- birthday or anniversary once per eligible period
- win-back cooldown
- complaint recovery suppression

Frequency caps must be enforced centrally rather than reimplemented separately for each campaign.

### 3.13 Campaign execution

- Campaign launch creates background jobs (ARQ).
- Recipient processing is chunked.
- Each recipient execution has an idempotency key.
- Delivery attempts are retried only for retryable failures.
- Permanent failures do not retry indefinitely.
- Cancellation stops unsent jobs where possible.
- Already sent messages remain historically accurate.
- Provider callbacks are verified and deduplicated.
- Progress is based on stored recipient states, not browser state.

### 3.14 Recipient execution statuses

- pending
- suppressed
- queued
- sending
- sent
- delivered
- read
- clicked
- converted
- failed_retryable
- failed_permanent
- cancelled

Not every channel supports every state. Unsupported metrics must not be fabricated.

### 3.15 Campaign metrics

Core metrics:

- estimated audience
- resolved audience
- eligible audience
- suppressed recipients
- queued
- sent
- delivered
- read where available
- clicked where available
- conversions
- attributed orders
- attributed reservations
- attributed leads
- attributed revenue
- discount cost
- loyalty cost
- refund-adjusted revenue
- delivery rate
- conversion rate
- revenue per eligible recipient
- average attributed order value
- unsubscribe or opt-out count
- complaint count associated with campaign

Metric formulas must be centrally defined and documented.

### 3.16 Attribution

Supported attribution principles:

- Campaign attribution must be explicit and deterministic.
- Direct coupon usage may produce strong attribution.
- Tracked link or campaign reference may produce direct attribution.
- Order or reservation creation within an approved attribution window may produce time-window attribution when rules allow.
- Manual attribution requires permission and audit history.
- One transaction must not be fully counted against multiple campaigns unless the reporting definition explicitly supports multi-touch analysis.
- Cancelled orders and fully refunded value must not remain counted as realized campaign revenue.

Reports must state the attribution model and window.

### 3.17 Campaign dummy fixtures

Development fixtures may include:

- `RKPR-WINBACK-01`: a win-back campaign for customers with no completed order in the configured inactivity period
- `RKPR-LOYALTY-01`: a loyalty engagement campaign
- `RKPR-PIZZA-01`: a Paneer Tikka Pizza promotional campaign
- `RKPR-CORP-01`: corporate lunch outreach including the established BrightWave Technologies example

These are seed fixtures only. Their dates, recipient counts, and performance values must not be treated as production commitments.

### 3.18 Campaign edge cases

- consent withdrawn after scheduling but before send
- campaign paused while recipient jobs are queued
- offer expires during campaign
- product becomes unavailable
- template provider approval is revoked
- duplicate provider callback
- customer merged after audience resolution
- campaign owner disabled
- recipient converts before message delivery callback
- order later cancelled or refunded
- send partially succeeds before system timeout
- scheduled job runs twice
- audience definition changes after approval

### 3.19 Campaign acceptance criteria

- all marketing sends are consent-aware
- campaigns require appropriate approval
- audience is recalculated at execution
- recipient jobs are idempotent
- suppressions are explainable
- delivery states are provider-grounded
- unavailable metrics are not invented
- attribution rules are consistent
- cancelled and refunded transactions adjust reporting
- campaign pages remain responsive at high recipient volume

## 4. CUSTOMER SEGMENTATION AND AUDIENCES

### 4.1 Purpose

Segmentation groups customers for analysis, service, loyalty, and controlled campaign targeting.

Segments may be static or dynamic. Dynamic segments are defined by rules and recomputed through approved jobs or bounded queries.

### 4.2 Segment types

- dynamic
- static
- system
- campaign_snapshot

System segments are centrally managed and cannot be casually edited.

Campaign snapshots preserve the resolved audience used for an execution without replacing current customer state.

### 4.3 Segment statuses

- draft
- active
- paused
- archived
- invalid

### 4.4 Segment fields

- segment code
- name
- description
- type
- status
- owner
- rule definition
- estimated size
- last computed size
- last computed time
- refresh schedule where approved
- inclusion logic
- exclusion logic
- tags
- created by
- updated by
- version

### 4.5 Supported rule dimensions

Subject to available data and permission:

- customer status
- customer type
- customer segment label
- city or delivery zone
- preferred language
- dietary preference
- allergy flag only where permitted and appropriate
- loyalty tier
- loyalty balance range
- total completed orders
- completed order value
- average order value
- last completed order date
- visit frequency
- reservation history
- reservation no-show history
- product or category purchase history
- coupon usage
- campaign engagement
- feedback score
- complaint recovery state
- corporate account association
- lead stage or source where applicable
- consent state by channel
- birthday or anniversary month where stored with a valid purpose

Sensitive data must not be used for targeting without an approved basis.

### 4.6 Dynamic segment examples

- repeat customers
- high-value customers
- customers with no completed order in the configured inactivity window
- active loyalty members
- customers eligible for birthday communication
- customers who purchased Paneer Tikka Pizza
- corporate prospects
- customers with unresolved service recovery
- reservation guests with repeated visits

The exact threshold values must be configuration-backed or explicitly approved, not embedded as arbitrary code constants.

### 4.7 Segment builder

The builder must support:

- grouped conditions
- AND and OR logic
- explicit exclusion groups
- preview of normalized rule definition
- estimated member count
- sample member preview with permission
- validation of unsupported combinations
- versioning
- duplicate-name prevention
- warning for overly broad audiences
- warning for no consent-compatible recipients

### 4.8 Segment computation

- Computation must use indexed fields and bounded execution.
- Large recalculations run asynchronously (ARQ worker).
- Each computation records start time, end time, outcome, member count, and error summary.
- Segment membership may be materialized where required for performance.
- Stale state must be visible.
- Failed refresh must not silently reuse stale data without disclosure.

### 4.9 Static segment management

Members may be added through:

- authorized manual selection
- validated import
- conversion from a dynamic snapshot
- campaign outcome workflow

Every manual addition or removal records actor, reason, and time.

### 4.10 Segment use restrictions

A segment may be used for a campaign only when:

- it is active
- its rules are valid
- its data is sufficiently fresh
- the user has permission to access the member data
- campaign consent rules are independently satisfied

Segment membership never overrides consent.

### 4.11 Segmentation acceptance criteria

- rules are versioned
- current membership is explainable
- computation is scalable
- stale or failed state is visible
- sensitive targeting is restricted
- campaign eligibility rechecks consent
- static membership changes are audited

## 5. LOYALTY AND REWARDS

### 5.1 Purpose

The Loyalty module supports customer retention through a controlled points and tier system.

It must provide complete financial and operational traceability. Loyalty points cannot be represented only by an editable balance.

### 5.2 Loyalty account statuses

- active
- suspended
- closed
- merged

### 5.3 Loyalty account fields

- loyalty account number
- customer ID
- status
- current points balance
- lifetime points earned
- lifetime points redeemed
- lifetime points expired
- tier
- tier effective time
- tier review time
- enrollment source
- enrollment time
- terms version accepted where required
- suspension reason
- created time
- updated time

### 5.4 Loyalty ledger

Every balance change creates an immutable ledger entry.

Ledger entry types:

- earn_order
- earn_campaign
- earn_manual
- redeem_order
- redeem_reward
- expire
- reverse_earn
- reverse_redemption
- service_recovery_credit
- merge_transfer
- correction

Ledger fields:

- ledger entry ID
- loyalty account ID
- entry type
- points delta
- balance after entry
- source record type
- source record ID
- idempotency key
- description
- effective time
- expiry time where applicable
- created by or system actor
- approval reference where required
- reversal linkage

Ledger rows are never edited to change history. Corrections use compensating entries.

### 5.5 Earning rules

Earning rules may depend on:

- eligible completed order value
- product or category bonus
- campaign bonus
- enrollment event
- approved service recovery
- tier multiplier

Rules must specify:

- code
- name
- active period
- eligible transaction state
- eligible monetary base
- excluded taxes, fees, discounts, or products where applicable
- calculation method
- rounding method
- points cap
- customer eligibility
- reversal behavior

Points must not be finally earned from unpaid, cancelled, or fully refunded orders.

### 5.6 Redemption rules

Redemption requires:

- active loyalty account
- sufficient available balance
- eligible order or reward
- minimum redemption threshold where configured
- maximum redemption limit where configured
- no duplicate redemption
- authorized transaction state

Redemption must occur inside a transaction that prevents overspending the same points concurrently.

### 5.7 Points expiry

Where expiry is enabled:

- expiry policy must be explicit
- expiring points must be traceable to earning buckets or a deterministic allocation method
- reminders may be sent only under valid communication rules
- expiry jobs must be idempotent
- expired points create ledger entries
- backdated changes must not corrupt historical balances

### 5.8 Loyalty tiers

Example tier codes may be configured, but no tier threshold is authoritative until approved in configuration.

Tier behavior may include:

- eligibility threshold
- evaluation window
- tier validity period
- earning multiplier
- approved benefits
- downgrade protection where configured

Tier changes create history records and notifications where permitted.

### 5.9 Manual adjustments

Manual adjustments require:

- permission (`loyalty.adjust`)
- reason
- points amount
- linked customer or service event
- approval when above configured threshold
- audit history

Negative adjustments cannot reduce the balance below allowed limits unless the correction workflow explicitly supports a controlled debt state.

### 5.10 Loyalty account page

Displays:

- customer identity
- current balance
- tier
- points expiring soon
- lifetime earned
- lifetime redeemed
- recent ledger
- available rewards where implemented
- linked orders
- campaign bonus history
- service recovery credits
- adjustment history

### 5.11 Loyalty reporting

- active members
- enrollment trend
- points issued
- points redeemed
- points expired
- outstanding points liability using the approved financial method
- redemption rate
- repeat-order rate for members
- average order value for members
- tier distribution
- campaign bonus performance
- manual adjustment volume
- service recovery credit volume

Financial liability calculations must use an approved methodology rather than an invented conversion value.

### 5.12 Loyalty edge cases

- order completed twice by duplicate event
- order refunded after points earned
- redemption succeeds but payment fails
- customer accounts merged
- loyalty account suspended during redemption
- concurrent redemptions
- expired points later affected by order reversal
- manual correction to historical error
- campaign bonus executed twice

### 5.13 Loyalty acceptance criteria

- ledger and balance reconcile
- entries are idempotent
- no concurrent overspending
- refunds and cancellations reverse correctly
- manual adjustments are controlled
- tier changes are historical
- financial reports use approved methods
- customer merges preserve all history

## 6. OFFERS, COUPONS, AND PROMOTIONS

### 6.1 Purpose

This module defines controlled price incentives used across orders, campaigns, loyalty, and service recovery.

### 6.2 Offer types

- percentage_discount
- fixed_discount
- item_discount
- category_discount
- buy_x_get_y
- combo_price
- free_item
- delivery_fee_discount
- loyalty_bonus
- service_recovery

### 6.3 Offer statuses

- draft
- in_review
- approved
- active
- paused
- expired
- cancelled
- archived

### 6.4 Offer fields

- offer code
- name
- description
- type
- status
- eligibility rule
- benefit rule
- minimum order value
- maximum discount
- applicable products or categories
- excluded products or categories
- customer eligibility
- channel eligibility
- usage start and end
- daily time window where applicable
- global usage limit
- per-customer usage limit
- stackability rules
- coupon requirement
- campaign linkage
- approval data
- financial owner
- created and updated metadata

### 6.5 Coupon fields

- coupon code
- linked offer
- status
- reusable or single-use state
- customer assignment where applicable
- start and expiry
- redemption limit
- redemption count
- source campaign
- generation batch
- created time

Coupon codes must be normalized and uniqueness-enforced.

### 6.6 Promotion evaluation order

The system must define one deterministic order for:

- item-level promotions
- combo pricing
- order-level discounts
- coupon discount
- loyalty redemption
- taxes and fees

The approved order must match the financial logic in `DATABASE_AND_API.md` and the order behavior in `CORE_CRM_MODULES.md`.

The same order must be used in preview, checkout, persisted order totals, invoices, refunds, and reports.

### 6.7 Promotion validation

- active time window
- active offer and coupon
- customer eligibility
- channel eligibility
- required product eligibility
- minimum value
- usage limit
- stackability
- existing redemption
- current menu and product status
- maximum discount

Promotion evaluation must happen server-side.

### 6.8 Promotion history

Each applied discount stores:

- offer and coupon reference
- rule version
- pre-discount eligible amount
- discount amount
- evaluation result
- application order
- actor or channel
- timestamp

Later changes to the offer cannot rewrite historical order calculations.

### 6.9 Promotion reports

- redemptions
- discount value
- attributed revenue
- average order value
- incremental repeat orders where measurable
- new versus existing customers
- product mix
- failed coupon attempts
- service recovery usage
- abuse indicators

### 6.10 Promotion edge cases

- coupon expires during checkout
- two concurrent uses of last available redemption
- item removed after coupon validation
- order partially refunded
- customer merged
- offer paused after cart preview
- offline or delayed order submission
- coupon entered with different casing

### 6.11 Promotion acceptance criteria

- evaluation is deterministic
- server is authoritative
- limits are concurrency-safe
- order history preserves rule version
- refunds allocate discounts correctly
- reports reconcile with orders
- abuse controls are available

## 7. REFERRAL PROGRAM

### 7.1 Purpose

The referral module lets an existing customer earn a reward for bringing a new customer whose first qualifying order is confirmed. It is a controlled extension of the Loyalty ledger (§5.4) — referral rewards post through the same ledger as `referral_reward` entries; there is no separate untracked reward balance.

Added to canonical scope on 2026-07-30, by explicit user decision, alongside §8-§10 below (`ROADMAP.md` Phase 12 completion notes record the decision).

### 7.2 Referral program configuration

- program code and name
- active window (start/end)
- referrer eligibility (e.g. active loyalty account, minimum tenure)
- referred-customer eligibility (must be a genuinely new customer identity)
- qualifying event: normally the referred customer's first completed, paid, direct order at or above a configured minimum value
- referrer reward and referee reward (points, and/or internal credit per §10)
- per-referrer limits (max active codes, max rewarded referrals per window)
- reward hold/delay period before the reward is posted, to absorb refund/cancellation risk
- lifecycle: draft, active, paused, archived
- version number (configuration snapshots referenced by relationship rows, not mutated in place)

### 7.3 Referral codes and relationships

Each referrer is issued a normalized, unique referral code. A referral relationship row records:

- referrer customer
- code used
- referred customer or contact (phone/email identity, resolved to a customer once one exists)
- attribution timestamp (when the code was captured — order, lead form, or manual entry)
- qualifying order reference
- status: `invited`, `attributed`, `qualified`, `rewarded`, `rejected`, `cancelled`
- rejection/fraud reason where applicable
- program and version reference

### 7.4 Anti-abuse rules

- a customer cannot refer themselves (referrer and referred identity must not resolve to the same customer, checked against normalized phone/email)
- a referred-contact identity (normalized phone or email) may be attributed to at most one referral relationship — no duplicate referee attribution
- a single qualifying order rewards at most one referral relationship
- rewards are posted only after the qualifying order reaches its confirmed/completed state and survives the hold period — never before confirmed qualification
- repeated attribution attempts using the same contact identity across different referrer codes are flagged for review (§commercial risk controls, see the new §10 permissions group and `commercial_risk.*` capability referenced in `DATABASE_AND_API.md`)

### 7.5 Referral acceptance criteria

- referral rewards use the canonical Loyalty ledger, not an untracked balance
- self-referral and duplicate-referee attribution are structurally prevented, not just discouraged
- a qualifying order rewards a relationship exactly once, even under retried/duplicate webhook or job execution
- rejected/cancelled relationships never post a reward
- referral history survives customer merges (Phase 5 merge semantics apply)

## 8. ACHIEVEMENTS AND BADGES

### 8.1 Purpose

Achievements are deterministic, configurable recognitions awarded when a customer's order/visit/referral history crosses a defined milestone. They are a lightweight retention/engagement layer, not a generic gamification platform — no scripting, no user-defined logic beyond the same constrained rule schema used by offers and segments (§6.6-6.7, §9 below).

Added to canonical scope on 2026-07-30, by explicit user decision (see §7.1).

### 8.2 Achievement definition fields

- code and name
- description and icon/visual metadata (for display only)
- condition version (a snapshot of the constrained rule the achievement evaluates against)
- supported condition facts: first completed order, order-count milestone, lifetime-spend milestone, visit-count milestone, referral milestone, loyalty-program anniversary, and other reliable order/visit facts already available in the CRM (the same fact list as §9.5 below)
- active/hidden status
- optional reward: points and/or internal credit, posted through the canonical ledgers (§5.4, §10.4) when the achievement is awarded — never a separate balance
- repeatability: one-time or repeatable-with-cooldown

### 8.3 Customer achievement awards

- immutable once created — an award is never edited, only reversed through a compensating ledger entry if its triggering event is later reversed (e.g. the qualifying order is refunded)
- idempotent: the same triggering event (identified by its own idempotency key) can never produce two awards for the same achievement and customer
- records the source event, awarded timestamp, and any reward-ledger linkage

### 8.4 Achievement acceptance criteria

- awarding is deterministic and reproducible from the same input facts
- duplicate/retried evaluation never double-awards
- reward issuance reuses the Loyalty or internal-credit ledger, never an untracked balance
- reversal of a triggering event correctly reverses any associated reward via a compensating entry

## 9. GIFT CARDS

### 9.1 Purpose

Restaurant-issued, redeemable stored value that a customer purchases or receives and later redeems against an order. This is restaurant-issued promotional/retail value, not a regulated stored-value or payment instrument — no claim of payment-services or e-money regulatory compliance is made anywhere in this system. The restaurant is responsible for confirming its own regulatory obligations before selling gift cards in production; this module only provides the operational ledger and lifecycle.

Added to canonical scope on 2026-07-30, by explicit user decision (see §7.1).

### 9.2 Gift card statuses

- `draft` — created but not yet activated (e.g. awaiting payment capture)
- `active` — usable for redemption
- `partially_redeemed`
- `fully_redeemed`
- `expired`
- `suspended` — temporarily blocked (suspected fraud, dispute)
- `cancelled`

### 9.3 Gift card fields

- public code/token (securely generated, never sequential or guessable) and a masked display form for lists (e.g. `****-****-1234`)
- optional PIN, stored only as a salted hash using the repository's existing password/security hashing utility — never plaintext
- purchaser customer/contact and recipient name/contact (may differ — gift cards can be bought for someone else)
- initial amount (integer minor units, per the project's money convention — §5.3 of `DATABASE_AND_API.md`)
- currency (INR only, matching every other monetary field in this system)
- cached current balance, always re-derivable from the ledger (§9.4)
- status (§9.2)
- issued/purchased/activated/expiry timestamps
- source order/payment reference where sold through an order
- delivery status where sent via the Communication Hub (§3, existing Phase 10 channels)
- notes and metadata

### 9.4 Gift card ledger

Every balance change creates an immutable entry:

- `issue` — card created with its initial amount
- `activate` — card made usable (may be combined with `issue` for cards sold and activated in the same step)
- `redeem` — value applied to an order
- `reverse` — a redemption is reversed via a compensating entry (never a destructive edit)
- `adjust` — manual correction, requires a reason and the acting staff actor
- `expire`
- `cancel`
- `migration`

Each entry carries: immutable ID, gift-card reference, entry type, signed amount, balance-after snapshot, idempotency key, source reference (order/payment/staff action), reason, effective timestamp, and created-by actor.

### 9.5 Redemption rules

- validate status is `active` or `partially_redeemed` and the card is not expired or suspended before allowing redemption
- support partial redemption — a redemption never exceeds the current balance, and the balance can never go negative
- redemption locks the balance row (or uses an equivalent concurrency-safe pattern already established for the project's other balance-derived entities, e.g. inventory balances in `DATABASE_AND_API.md` §7) so two concurrent redemption attempts cannot both succeed against the same remaining balance
- redemption is idempotent against its own idempotency key
- redemption links to the order/payment allocation it was applied against, using the same deterministic stacking order as §6.6/§9.6 below
- a redemption can be reversed only through a compensating `reverse` ledger entry, never by editing the original `redeem` entry

### 9.6 Security

- codes are generated using a cryptographically secure random source, sized to resist brute-force guessing
- PINs, where used, are salted-hashed, never stored or logged in plaintext
- viewing an unmasked code/PIN requires a dedicated permission (`gift_cards.reveal_sensitive`) separate from ordinary view access
- issuance above a configurable value threshold requires the appropriate elevated permission and, where configured, a second-approval step (§commercial risk controls)

### 9.7 Gift card acceptance criteria

- balance is always derivable from, and reconciles with, the ledger
- no negative balance is ever possible, including under concurrent redemption attempts
- codes/PINs are never exposed in logs, audit metadata, or unmasked API responses without the reveal permission
- reversal uses compensating entries only
- delivery, where used, flows through the existing Communication Hub, not a new channel

## 10. INTERNAL CUSTOMER CREDIT

### 10.1 Purpose

An internal, non-withdrawable promotional and service-recovery credit ledger. It exists to let staff issue goodwill or service-recovery value that a customer can apply toward a future order — it is explicitly **not** a bank account, prepaid payment instrument, cash wallet, payment processor, or withdrawable balance.

Added to canonical scope on 2026-07-30, by explicit user decision (see §7.1). This is a deliberate design divergence from §5.4's existing `service_recovery_credit` Loyalty-ledger entry type: `service_recovery_credit` remains valid for *small*, points-denominated goodwill gestures recorded on the Loyalty ledger; the internal-credit ledger below is for *money-denominated* store credit (e.g. "₹500 off your next order") that is not naturally expressed as loyalty points. Both mechanisms may coexist; staff guidance on which to use for a given situation is an operational decision, not a schema one.

### 10.2 Hard restrictions

- no cash withdrawal, under any circumstance
- no customer-to-customer transfer
- no customer top-up (credit can only be issued by staff/system events — a customer cannot add their own money to this ledger)
- no interest or time-value accrual
- no external payment rail integration
- available balance can never go negative
- issuance above a configurable threshold requires the appropriate permission and, where configured, approval (§commercial risk controls)

### 10.3 Credit account fields

- customer reference
- cached current balance, always re-derivable from the ledger
- status (active/suspended/closed, mirroring §9.2's gift-card status vocabulary where meaningful)
- created/updated metadata

### 10.4 Credit ledger entry types

- `issue` — service recovery
- `issue` — approved refund issued as store credit rather than a payment-rail refund
- `issue` — campaign reward
- `issue` — referral reward (§7.3)
- `issue` — goodwill adjustment
- `migration`
- `redeem` — applied against an order
- `reverse` — compensating entry
- `expire` — only where an explicit expiry policy is configured; default is no expiry

Each entry carries the same immutable-ledger shape as §5.4 and §9.4: ID, account reference, entry type, signed amount, balance-after snapshot, idempotency key, source reference, reason, effective timestamp, and created-by actor. Entries are never edited; corrections are compensating entries.

### 10.5 Redemption rules

Redemption against an order follows the same concurrency-safety, idempotency, and non-negative-balance rules as gift-card redemption (§9.5), and participates in the same deterministic stacking/allocation order as every other discount/value mechanism (§6.6).

### 10.6 Internal credit acceptance criteria

- balance is always derivable from, and reconciles with, the ledger
- no negative balance is ever possible
- no code path allows cash withdrawal, transfer, top-up, or external payout
- manual issuance above threshold requires the correct permission and audit trail
- redemption participates correctly in the canonical stacking order and never allows total applied value to exceed the order's payable amount

## 11. FEEDBACK AND REVIEWS

### 11.1 Purpose

The Feedback module collects, organizes, analyses, and resolves customer sentiment linked to orders, reservations, campaigns, and general restaurant experiences.

### 11.2 Feedback sources

- post_order
- post_reservation
- website
- whatsapp
- email
- manual_entry
- public_review_reference
- campaign

Public review references may store permitted metadata and links. The system must not claim direct platform integration unless it exists.

### 11.3 Feedback statuses

- new
- acknowledged
- under_review
- action_required
- resolved
- closed
- spam

### 11.4 Feedback fields

- feedback number
- customer or guest
- source
- linked order
- linked reservation
- linked campaign
- rating
- category ratings where collected
- free-text comment
- sentiment label where generated
- consent for follow-up where required
- assigned staff
- status
- priority
- acknowledgement time
- resolution time
- follow-up outcome
- created time
- updated time

### 11.5 Rating dimensions

Where collected:

- food_quality
- taste
- packaging
- delivery
- speed
- staff_service
- cleanliness
- reservation_experience
- value
- overall

The UI must clearly distinguish missing ratings from low ratings.

### 11.6 Feedback request workflow

1. Eligible source event occurs, such as a completed order.
2. Delay and communication eligibility are checked.
3. Request job is created idempotently (ARQ worker).
4. Customer receives an approved request.
5. Submitted feedback is linked to the source record.
6. Low ratings or urgent language trigger review.
7. Staff acknowledges where required.
8. Complaint or service recovery record is created when appropriate.
9. Resolution and follow-up are recorded.

### 11.7 Feedback list page

Columns:

- feedback number
- customer
- source
- overall rating
- key category
- sentiment indicator
- status
- priority
- linked record
- assigned staff
- created time

Saved views:

- New
- Low rating
- Action required
- Unassigned
- My feedback
- Resolved recently
- Campaign feedback
- Order feedback
- Reservation feedback

### 11.8 Feedback detail page

- customer summary
- rating breakdown
- original comment
- linked order or reservation context
- communication history
- internal notes
- complaint linkage
- service recovery actions
- follow-up response
- timeline
- audit history

### 11.9 Sentiment analysis

AI may provide an advisory sentiment label (available only from Phase 14 onward):

- positive
- neutral
- negative
- mixed
- urgent_review

Requirements:

- label is visibly AI-generated
- original feedback remains primary
- confidence or uncertainty is available where supported
- low-confidence analysis must not drive silent automation
- safety, legal, discrimination, payment, allergy, or serious service concerns must be escalated through deterministic rules where possible

### 11.10 Feedback metrics

- response rate
- average overall rating
- rating distribution
- category averages
- low-rating count
- acknowledgement time
- resolution time
- repeat complaint rate
- feedback by product
- feedback by order channel
- feedback by reservation
- campaign feedback
- service recovery satisfaction where collected

### 11.11 Feedback dummy fixtures

Fixtures may reference the established sample customers:

- Ananya Rao providing product feedback related to Paneer Tikka Pizza
- Rahul Mehta reporting a delayed delivery experience
- Shreya Kulkarni commenting on a Jain preparation request
- BrightWave Technologies providing corporate order feedback

These are development examples only.

### 11.12 Feedback edge cases

- anonymous feedback later matched to customer
- duplicate submission
- feedback submitted before order completion
- rating without comment
- comment without rating
- public review edited externally
- customer requests deletion subject to retention requirements
- feedback linked to merged customer
- AI sentiment differs from staff assessment

### 11.13 Feedback acceptance criteria

- source linkage is accurate
- duplicates are controlled
- low ratings are actionable
- AI remains advisory
- missing data is not misrepresented
- feedback metrics use consistent denominators
- service recovery history is preserved

## 12. COMPLAINTS AND SERVICE RECOVERY INTELLIGENCE

### 12.1 Purpose

Complaints are operational records requiring ownership, severity assessment, resolution, and learning. They may originate from feedback, conversations, orders, reservations, campaigns, or manual entry.

### 12.2 Complaint categories

- food_quality
- incorrect_item
- missing_item
- packaging
- delay
- delivery
- payment
- refund
- reservation
- staff_behavior
- cleanliness
- allergy_or_dietary
- promotion
- loyalty
- communication
- corporate_order
- other

### 12.3 Complaint severities

- low
- medium
- high
- critical

Severity rules must be explicit. Critical concerns may include safety, allergy, serious payment disputes, legal threats, or repeated unresolved failures.

### 12.4 Complaint statuses

- new
- acknowledged
- investigating
- awaiting_customer
- awaiting_internal
- resolution_proposed
- resolved
- closed
- reopened

### 12.5 Complaint fields

- complaint number
- customer or guest
- category
- severity
- source
- linked records
- description
- desired resolution
- owner
- responsible team
- status
- first response due
- resolution target
- root cause
- resolution type
- approved compensation
- customer response
- reopened count
- created time
- acknowledged time
- resolved time
- closed time

### 12.6 Service recovery types

- apology_only
- replacement
- refund_request
- approved_refund
- discount
- coupon
- loyalty_credit
- complimentary_item
- manager_follow_up
- operational_correction

Compensation must use the correct order, loyalty, or promotion module. Complaint screens cannot directly mutate financial history without the approved workflow.

### 12.7 Root-cause categories

- process_failure
- preparation_error
- inventory_unavailable
- packaging_error
- delivery_delay
- staff_training_gap
- communication_failure
- system_failure
- supplier_issue
- policy_gap
- customer_expectation_mismatch
- unknown

Root cause may be updated as investigation progresses, with history retained.

### 12.8 Complaint intelligence

Reports may identify:

- repeated complaint categories
- products with elevated complaint rate
- channels with elevated delay complaints
- repeated customer service failures
- supplier-linked quality concerns
- promotion confusion
- reservation process failures
- training opportunities
- recurring root causes

Counts must be normalized where appropriate. For example, product complaint rate should use relevant product sales as the denominator rather than raw complaint count alone.

### 12.9 Complaint acceptance criteria

- every complaint has ownership
- severity and SLA rules are consistent
- compensation requires correct approval
- root-cause history is preserved
- reopened complaints remain traceable
- reports use meaningful denominators
- sensitive concerns are permission-controlled

## 13. REPORTS AND ANALYTICS

### 13.1 Purpose

Reports and Analytics provide trusted, bounded, permission-aware operational and growth insights.

They must not become an unrestricted query engine over raw production tables.

### 13.2 Reporting areas

- executive overview
- sales
- orders
- customers
- leads
- reservations
- menu and products
- inventory and suppliers
- marketing
- loyalty
- feedback
- complaints
- communication
- staff and tasks
- system operations

### 13.3 Reporting windows

Supported common windows:

- today
- yesterday
- current week
- previous week
- current month
- previous month
- current quarter
- previous quarter
- custom bounded range

Comparisons must clearly state the comparison period.

### 13.4 Metric definition contract

Every production metric must define:

- metric code
- display name
- business definition
- numerator
- denominator where applicable
- included record states
- excluded record states
- time basis
- currency basis
- refund and cancellation treatment
- data source
- freshness
- permitted dimensions
- owner
- version

Metric definitions must not live only in frontend code.

### 13.5 Executive metrics

May include:

- gross sales
- net sales
- completed orders
- average order value
- new customers
- repeat customer rate
- reservation requests
- reservation conversion
- active leads
- lead conversion
- loyalty members
- campaign-attributed revenue
- average feedback rating
- open high-severity complaints
- critical inventory items
- overdue operational tasks

### 13.6 Sales metrics

- gross item value
- discounts
- taxes
- fees
- refunds
- net sales
- completed order count
- cancelled order count
- average order value
- sales by order channel
- sales by product
- sales by category
- sales by daypart
- sales by customer segment
- payment method distribution where available

Definitions must match persisted order totals and financial states.

### 13.7 Customer metrics

- total customers
- new customers
- active customers
- repeat customers
- order frequency
- recency
- average order value
- customer lifetime value using an approved formula
- loyalty enrollment
- consent coverage
- segment distribution
- churn-risk indicator where defined
- complaint recovery customers

Customer lifetime value must not be presented without an explicit formula and time horizon.

### 13.8 Lead metrics

- new leads
- open leads
- qualified leads
- won leads
- lost leads
- conversion rate
- pipeline value
- weighted pipeline value
- average time in stage
- overdue follow-ups
- lead source performance
- corporate lead performance

### 13.9 Reservation metrics

- requests
- confirmed
- rejected
- cancelled
- no-show
- seated or completed where tracked
- conversion rate
- average party size
- table utilization where reliable
- lead time between booking and reservation
- repeat guest rate
- special request volume

### 13.10 Product metrics

- quantity sold
- gross sales
- discount value
- net sales
- average selling price
- estimated food cost using approved recipe costs
- estimated contribution margin
- cancellation or refund association
- feedback rating
- complaint rate
- stock-out impact
- modifier popularity

Cost and margin values must visibly disclose when ingredient cost data is missing or stale.

### 13.11 Inventory metrics

- current stock value
- low-stock items
- critical-stock items
- stock movement volume
- consumption
- waste
- variance
- expiring batches
- supplier lead time
- purchase order cycle time
- stock-out frequency
- recipe consumption variance

### 13.12 Marketing metrics

As defined in the campaign section, including eligible recipients, delivery, conversion, attributed revenue, discount cost, opt-outs, and complaints.

### 13.13 Loyalty metrics

As defined in the loyalty section, including ledger movement, redemption, expiry, repeat ordering, tier distribution, and approved liability reporting.

### 13.14 Feedback and complaint metrics

- feedback response rate
- average rating
- low-rating rate
- complaint rate per relevant transaction volume
- complaint category distribution
- acknowledgement time
- resolution time
- reopen rate
- compensation value
- root-cause distribution
- recovery follow-up result

### 13.15 Report filters and dimensions

Depending on report:

- date range
- order channel
- product
- category
- customer segment
- loyalty tier
- campaign
- offer
- staff or team
- lead source
- reservation status
- complaint category
- supplier
- inventory category
- location if the architecture later supports approved additional locations

The current system must not introduce multi-tenant or multi-location assumptions unless explicitly approved elsewhere.

### 13.16 Dashboard freshness

Each widget shows or exposes:

- reporting window
- last refreshed time
- live, near-real-time, cached, or scheduled status
- partial-data warning where applicable
- failed-refresh state

### 13.17 Aggregation strategy

- Simple bounded metrics may query transactional tables using approved indexes.
- Expensive repeated calculations should use summary tables or materialized views where approved.
- Refresh jobs must be observable and idempotent (ARQ worker).
- Historical aggregates must reconcile with source records.
- Corrections, refunds, and late events must update affected reporting periods.
- Reports must avoid unbounded browser-side aggregation.

### 13.18 Export workflow

1. User selects report and bounded filters.
2. System validates permission (`reports.export`).
3. Small exports may execute directly within limits.
4. Large exports create background jobs.
5. Export file is stored privately.
6. User is notified on completion or failure.
7. Download uses a short-lived signed URL.
8. Export generation and download are audited where required.

### 13.19 Scheduled reports

Scheduled reports may support:

- recipient users or roles
- approved report definition
- fixed filters
- schedule
- output format
- delivery channel where implemented
- expiry of generated file

Schedules must not expose data to unauthorized recipients after a role change. Permission must be checked at generation and delivery time.

### 13.20 Report edge cases

- late refund changes previous period
- order status changes after aggregate refresh
- missing cost data
- duplicate webhook created duplicate source event but idempotency prevented duplicate transaction
- timezone boundary
- custom date range too large
- user loses permission before export completes
- report job succeeds but notification fails
- comparison period has no data
- denominator is zero

### 13.21 Reporting acceptance criteria

- metrics have definitions
- financial values reconcile
- refunds and cancellations are handled consistently
- freshness is visible
- expensive queries are bounded
- exports are private
- scheduled report permissions are rechecked
- missing or unreliable data is disclosed
- zero denominators do not produce misleading percentages

## 14. CONTROLLED AI CENTER

### 14.1 Purpose

The AI Center provides advisory assistance grounded in CRM data. It is controlled, permission-aware, auditable, and optional.

It is not an autonomous operator and does not replace deterministic business logic. It is implemented and credentialed only in Phase 14 of `ROADMAP.md`.

### 14.2 Allowed AI capabilities

- summarize customer history
- summarize conversations
- draft replies
- summarize lead status
- suggest lead next actions
- summarize campaign performance
- suggest campaign observations
- summarize feedback themes
- categorize feedback or complaints for review
- suggest root-cause hypotheses
- summarize product performance
- identify unusual changes in approved metrics
- summarize inventory risks from visible data
- draft Knowledge Base content
- suggest report narratives
- suggest questions for management review

### 14.3 Prohibited autonomous behavior

AI must not independently:

- send messages
- publish campaigns
- change campaign audiences
- alter consent
- approve discounts
- create or approve refunds
- alter loyalty balances
- change prices
- change menu availability
- place purchase orders
- make staff employment decisions
- approve leave
- assign sensitive roles
- publish policies
- delete records
- execute arbitrary database queries
- expose data outside the user's permission scope

### 14.4 AI request fields

Each AI request should retain where appropriate:

- request ID
- user
- feature
- input record references
- permission scope
- prompt template version
- model/provider configuration reference
- output
- grounding summary
- confidence or limitation metadata where supported
- user feedback
- accepted, edited, rejected, or ignored state
- created time
- latency
- token or cost metadata where available and permitted
- failure category

Secrets, raw credentials, and unnecessary sensitive data must never be stored in prompts or logs.

### 14.5 Grounding rules

- AI receives only data required for the task.
- Data access follows backend permissions.
- Source record references must be retained.
- Generated summaries should expose the relevant source timeline or records to the user.
- AI must state when required data is missing.
- AI must not infer a payment, refund, order, reservation, policy, or consent fact that is absent.
- Knowledge Base content may be included only from approved and accessible articles.
- No RAG, embeddings, vector search, or pgvector are introduced by this module.

### 14.6 AI output presentation

Every output must be visibly labelled as AI-generated or AI-assisted.

The UI should support:

- copy
- edit
- accept into a draft field
- reject
- regenerate where appropriate
- provide feedback
- view grounding references

AI output is never silently written into final records.

### 14.7 AI prompt management

Prompt templates must be versioned and centrally managed.

Each template defines:

- feature code
- purpose
- allowed input fields
- prohibited data
- output schema where structured
- maximum context size
- failure handling
- safety constraints
- model configuration reference
- active version

### 14.8 Structured AI output

Where AI classifies or suggests structured data:

- output must be schema-validated
- unknown values must be rejected or mapped to explicit `unknown`
- validation failure must not mutate records
- staff must review consequential suggestions

### 14.9 AI rate and cost controls

- per-user and per-feature rate limits
- maximum input size
- maximum output size
- timeout
- retry policy
- circuit breaker
- daily or monthly cost monitoring where available
- graceful fallback when provider is unavailable

Ordinary CRM workflows must remain usable during AI outage.

### 14.10 AI privacy and security

- minimize customer and staff data
- redact or exclude unnecessary sensitive fields
- restrict HR-related AI features
- avoid sending secrets or provider tokens
- record user and feature audit data
- apply retention rules
- ensure outputs cannot bypass permissions
- prevent prompt-injection content from being treated as system instructions

### 14.11 Prompt injection handling

Customer messages, feedback, uploaded text, and Knowledge Base content are untrusted data.

The AI layer must:

- separate system instructions from retrieved or user-provided text
- restrict tool availability
- never execute instructions embedded in customer content
- validate structured outputs
- avoid exposing hidden prompts or credentials
- treat external URLs and attachments as untrusted

### 14.12 AI performance reports

- requests by feature
- success rate
- latency
- provider failure rate
- user acceptance rate
- edit rate
- rejection rate
- cost where available
- safety-blocked requests
- grounding-missing failures

These reports must not expose sensitive prompt content to unauthorized users.

### 14.13 AI acceptance criteria

- all features are advisory
- permissions are enforced before context assembly
- grounding references are retained
- structured outputs are validated
- AI outage does not block core CRM
- customer-facing output requires review
- sensitive autonomous actions are impossible
- prompt injection defenses are tested
- no RAG or vector architecture is added

## 15. FORECASTING AND DECISION SUPPORT

### 15.1 Purpose

Decision Support helps managers interpret historical and current data. Forecasts must be transparent, versioned, and clearly distinguished from actuals.

### 15.2 Supported forecast areas

Potential approved forecasts:

- order volume
- sales
- product demand
- ingredient demand
- reservation volume
- campaign response
- staffing demand indicators

Forecasting features may be enabled only when sufficient historical data exists.

### 15.3 Forecast fields

- forecast ID
- forecast type
- generated time
- historical window
- forecast horizon
- dimensions
- model or method version
- input data completeness
- forecast values
- confidence interval where supported
- assumptions
- accuracy metrics when actuals become available
- status

### 15.4 Forecasting rules

- Forecasts are advisory.
- Actual records remain authoritative.
- Forecast horizon must be visible.
- Missing-data warnings must be visible.
- Holiday, campaign, menu, closure, and stock-out effects should be included only when represented by available data or explicit assumptions.
- Forecasts must not automatically place purchase orders, change staffing, or change menu availability.
- Managers may create tasks or planning actions from forecasts.

### 15.5 Baseline before complexity

Initial forecasting should begin with explainable statistical baselines before more complex methods are approved.

The chosen method must be appropriate to data volume, seasonality, and operational value. No model name or external forecasting tool should be invented as a fixed decision unless approved in the architecture or `TOOLS.md`.

### 15.6 Forecast evaluation

When actuals become available, track suitable metrics such as:

- absolute error
- percentage error where denominator is meaningful
- bias
- interval coverage where supported

A forecast with insufficient data must show `insufficient_data` rather than a fabricated number.

### 15.7 Anomaly detection

Allowed advisory anomalies:

- unusual drop or spike in sales
- elevated cancellation rate
- unusual complaint rate
- sharp delivery delay change
- unexpected inventory consumption
- supplier lead-time deterioration
- campaign performance deviation

Anomaly alerts require:

- metric definition
- baseline window
- observed value
- expected range or comparison
- severity
- supporting data
- acknowledgement state

### 15.8 Forecasting acceptance criteria

- actuals and forecasts are clearly separated
- methodology is versioned
- insufficient data is disclosed
- forecasts do not execute operations automatically
- forecast accuracy is measured
- anomalies link to supporting records or reports

## 16. GROWTH DASHBOARDS

### 16.1 Executive growth dashboard

Suggested widgets:

- net sales trend
- completed orders
- average order value
- new versus repeat customers
- repeat order rate
- loyalty enrollment and redemption
- active campaigns
- campaign-attributed revenue
- customer segments
- feedback rating
- open high-severity complaints
- top products
- products needing attention
- corporate pipeline

### 16.2 Marketing dashboard

- active and scheduled campaigns
- eligible recipients
- delivery rate
- conversion rate
- attributed revenue
- discount cost
- opt-outs
- failed sends
- audience growth
- top-performing campaigns

### 16.3 Customer intelligence dashboard

- new customers
- active customers
- repeat customers
- recency distribution
- frequency distribution
- monetary distribution
- loyalty tier distribution
- consent coverage
- high-value customer trend
- win-back opportunity count
- complaint recovery cohort

### 16.4 Experience dashboard

- feedback volume
- average rating
- category ratings
- complaint rate
- top complaint categories
- acknowledgement time
- resolution time
- repeated root causes
- recovery outcomes

### 16.5 Dashboard behavior

- cards link to filtered detail pages
- filters remain permission-aware
- comparison periods are visible
- loading and stale states exist
- partial failures do not blank the whole dashboard
- widgets use bounded or pre-aggregated endpoints
- values are never generated by AI without being labelled

## 17. CROSS-MODULE GROWTH WORKFLOWS

### 17.1 New customer lifecycle

- customer completes first eligible order
- customer profile is created or matched
- new-customer metrics update
- loyalty enrollment may be offered under approved rules
- feedback request may be scheduled
- customer enters relevant dynamic segments
- future marketing requires consent

### 17.2 Repeat customer lifecycle

- completed orders update recency, frequency, and monetary metrics
- segment membership refreshes
- loyalty ledger updates
- appropriate campaigns may target the customer only after eligibility checks
- complaint history and service recovery state remain visible

### 17.3 Win-back workflow

- dynamic segment identifies eligible inactive customers
- campaign is created and approved
- current consent and suppressions are checked
- offer is linked where approved
- messages are sent idempotently
- conversions are attributed according to the defined window
- campaign results update reports

### 17.4 Loyalty redemption workflow

- customer selects redemption
- server validates account and balance
- points reservation or atomic redemption is created
- order financials are calculated deterministically
- successful transaction finalizes ledger entry
- failed or cancelled transaction reverses or releases points correctly
- reports reconcile

### 17.5 Low-rating recovery workflow

- feedback received
- rule detects low rating or urgent concern
- complaint created or linked
- manager notified according to severity
- recovery task assigned
- approved compensation executed in correct module
- customer follow-up recorded
- root cause and final outcome included in reports

### 17.6 Product performance workflow

- order data updates product sales metrics
- refunds and cancellations adjust actuals
- recipe and inventory data provide cost context where complete
- feedback and complaint rates are joined through approved reporting models
- management sees product performance and data-quality warnings
- any menu decision remains human-controlled

### 17.7 Corporate account growth workflow

Using the established BrightWave Technologies fixture:

- corporate lead is assigned to Nikhil Jain
- communication and follow-up tasks are recorded
- proposal and negotiation history remain linked
- won lead converts to corporate customer structure
- recurring orders and feedback are tracked
- revenue and service performance reports include the account

This is a development fixture, not a production customer commitment.

## 18. GROWTH NOTIFICATIONS

Possible actionable notifications:

- campaign awaiting approval
- campaign scheduled with invalid template
- consent-compatible audience dropped materially
- campaign execution failed
- campaign offer expiring
- unusual opt-out rate
- loyalty ledger reconciliation failure
- points expiring workflow failure
- high-value manual adjustment awaiting approval
- low feedback rating
- critical complaint
- repeated product complaint pattern
- report refresh failed
- scheduled report failed
- forecast data insufficient
- significant anomaly detected

Notifications must be deduplicated, permission-aware, and linked to the exact record or report.

## 19. PERMISSIONS

Permission groups map to the single canonical capability registry defined in `DATABASE_AND_API.md` §4.4 (dot-separated codes such as `campaigns.view`, `campaigns.create`, `campaigns.approve`, `campaigns.send`, `loyalty.view`, `loyalty.adjust`, `reports.view`, `reports.export`). This section lists the groups in plain language for product reference; the registry itself is the single source of truth:

- view marketing campaigns
- create campaigns
- review campaigns
- approve campaigns
- execute campaigns
- view campaign financials
- manage segments
- view segment members
- manage loyalty rules
- view loyalty accounts
- adjust loyalty points
- approve loyalty adjustments
- manage offers
- approve offers
- view feedback
- manage complaints
- approve service recovery
- view reports
- export reports
- schedule reports
- use AI features
- manage AI prompts and configuration
- view AI usage and cost
- view forecasts

Backend checks are authoritative.

## 20. PERFORMANCE REQUIREMENTS

- Campaign, segment, loyalty, feedback, and report lists use server-side pagination.
- Large audience resolution and campaign execution run asynchronously in the ARQ worker.
- Campaign metrics use aggregated recipient states.
- Loyalty balance reads use reconciled account state backed by ledger.
- Segment rules use indexed dimensions.
- Report endpoints are bounded.
- Large exports run as jobs.
- Dashboard widgets fail independently.
- AI calls never block ordinary record access.
- Forecast generation runs asynchronously where expensive.
- Realtime updates remain scoped to relevant records or job progress.

## 21. SECURITY AND COMPLIANCE REQUIREMENTS

- Consent is checked at send time.
- Marketing and operational communication are classified separately.
- Customer targeting is permission-controlled.
- Sensitive attributes are not casually exposed in segment builders.
- Loyalty and discount changes are audited.
- Financial actions require correct approval.
- Report exports are private.
- Scheduled report recipients are reauthorized.
- AI context is minimized and permission-scoped.
- Prompt injection is treated as a security threat.
- Provider credentials and raw secrets never appear in product screens or AI prompts.
- Public review or campaign integrations are shown only when actually configured.

## 22. TESTING REQUIREMENTS

Automated tests must cover:

- campaign status transitions
- campaign approval and version invalidation
- consent withdrawal before send
- suppression and frequency caps
- duplicate campaign execution
- attribution adjustments after cancellation or refund
- dynamic segment rule evaluation
- stale segment behavior
- loyalty earn, redeem, reverse, expire, merge, and concurrent redemption
- coupon limits and concurrency
- feedback request idempotency
- low-rating escalation
- complaint SLA and service recovery approval
- metric formulas
- zero-denominator handling
- report permission and export expiry
- AI permission scoping
- AI structured-output validation
- AI outage fallback
- forecast insufficient-data state
- anomaly deduplication

## 23. GROWTH AND INTELLIGENCE DEFINITION OF DONE

A module is complete only when:

- behavior matches this document
- data and API behavior matches `DATABASE_AND_API.md`
- architecture matches `ARCHITECTURE_AND_TECH_STACK.md`
- core workflows remain consistent with `CORE_CRM_MODULES.md`
- operational coordination matches `OPERATIONS_MODULES.md`
- dummy data remains consistent with `PROJECT_PLAN.md`
- important decisions never use dummy assumptions
- permissions are backend-enforced
- calculations are centrally defined and tested
- background execution is idempotent
- data quality limitations are visible
- loading, empty, stale, failure, and permission states exist
- sensitive actions are audited
- AI remains advisory and optional, and is only active from Phase 14 onward
- reports reconcile with authoritative records
- mobile and tablet behavior remains usable

## 24. FINAL GROWTH AND INTELLIGENCE COMMAND

Build the RKPR Restaurant CRM growth and intelligence features as trusted production restaurant software, not decorative dashboards or generic AI features. Marketing must be consent-aware and approval-controlled. Loyalty must be ledger-backed. Promotions must be deterministic. Feedback and complaints must lead to accountable recovery. Reports must use explicit definitions and reconcile with source records. AI and forecasting must remain advisory, grounded, permission-aware, and failure-tolerant. Preserve the established RKPR dummy data only for development fixtures, and never substitute dummy information for architecture, tools, providers, security, financial formulas, policies, permissions, or production decisions.
