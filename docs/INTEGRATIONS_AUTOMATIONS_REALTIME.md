# RKPR RESTAURANT CRM — INTEGRATIONS, AUTOMATIONS, AND REALTIME

## 1. DOCUMENT PURPOSE

This document defines the production behavior, boundaries, responsibilities, security controls, data contracts, event flows, automation rules, realtime delivery, retry handling, failure recovery, observability, and acceptance criteria for all RKPR Restaurant CRM integrations, background automations, and realtime features.

It must remain consistent with `PROJECT_PLAN.md`, `ARCHITECTURE_AND_TECH_STACK.md`, `DATABASE_AND_API.md`, `CORE_CRM_MODULES.md`, `OPERATIONS_MODULES.md`, and `GROWTH_AND_INTELLIGENCE.md`.

This document is authoritative for:

- external integration architecture
- integration configuration lifecycle
- inbound and outbound webhook behavior
- integration health and credential status
- background jobs and scheduled jobs
- domain events and the transactional outbox
- automation triggers, conditions, and actions
- retries, deduplication, idempotency, and dead-letter handling
- realtime notifications and record updates
- provider failure isolation
- integration audit history
- operational observability
- testing and definition of done

Dummy information is permitted only for development fixtures such as sample webhook events, test messages, sample integration records, and sample job histories. Important decisions such as providers, security, authentication, retry policy, data ownership, event contracts, credentials, production URLs, and compliance rules must never use invented dummy assumptions.

## 2. CORE PRINCIPLES

### 2.1 Backend-owned orchestration

All integrations and automations are backend capabilities. They are not implemented as independent browser-only workflows and are not represented as a separate generic automation-builder product.

The backend remains authoritative for:

- validating triggers
- evaluating permissions
- checking consent
- creating jobs
- calling providers
- processing callbacks
- changing domain state
- emitting realtime updates
- recording audit history

The frontend may request, configure, display, pause, resume, or inspect supported operations, but it never becomes the execution engine.

### 2.2 No separate n8n dependency

The approved architecture does not require n8n for core CRM automation. Background and scheduled processing use the approved application worker (ARQ), Redis-backed queue, PostgreSQL, and outbox patterns defined in the architecture documents.

An external automation platform must not be introduced without explicit approval in `TOOLS.md` and architecture review. n8n and Temporal are not approved for the current build.

### 2.3 Source-of-truth hierarchy

- PostgreSQL stores authoritative integration records, automation definitions, jobs, outbox events, webhook receipts, delivery attempts, audit history, and resulting domain state.
- Redis supports queues (ARQ transport), bounded locks, deduplication windows, rate limits, pub/sub, and short-lived coordination.
- External providers are authoritative only for provider-specific delivery or processing states that they own.
- Browser state is never the source of truth for job progress or realtime status.
- Provider dashboards do not replace internal operational records.

### 2.4 Deterministic business logic before automation

Automations must call the same domain services and validation rules used by manual API actions.

An automation must never bypass:

- permissions
- consent
- state-machine rules
- price validation
- order financial calculations
- inventory constraints
- approval rules
- idempotency
- audit logging

### 2.5 Human control

The following remain human-controlled unless a specific approved deterministic rule says otherwise:

- campaign approval
- marketing sends
- high-value refunds
- discretionary discounts
- loyalty adjustments
- complaint compensation
- staff employment changes
- supplier purchasing decisions
- menu pricing changes
- policy publication
- integration credential changes
- destructive data actions

### 2.6 Failure isolation

A provider outage must not make the entire CRM unavailable.

Examples:

- Email failure must not block order creation.
- WhatsApp failure must not block customer profile access.
- Realtime delivery failure must not corrupt the stored record.
- AI provider failure must not block ordinary CRM workflows.
- Export delivery failure must not erase a generated report.

### 2.7 Idempotency everywhere

Every externally triggered or retried operation that can create or mutate data must support deterministic deduplication.

Idempotency applies to:

- webhook ingestion
- campaign recipient execution
- feedback requests
- loyalty earning and reversal
- order status callbacks
- payment callbacks where implemented
- report generation
- notification creation
- scheduled jobs
- inventory deductions
- customer imports
- provider delivery callbacks

## 3. INTEGRATION CATEGORIES

Supported integration categories include:

- authentication and identity
- database and storage
- email
- WhatsApp
- SMS where approved
- website forms and chat
- payment or payment-status integration where implemented
- restaurant website ordering
- calendar and reservation notifications
- file storage and exports
- AI provider integration (Phase 14 only)
- analytics and observability
- supplier or external ordering interfaces only when explicitly approved
- public review references only when a real supported integration exists

The CRM must not display an integration as active unless:

- required configuration exists
- credential validation succeeds where supported
- health status is known
- required webhook registration is complete
- provider-specific prerequisites are satisfied

## 4. INTEGRATION CONFIGURATION MODEL

### 4.1 Integration record fields

Each integration record should include:

- integration ID
- integration code
- integration category
- provider code
- display name
- status
- environment
- enabled state
- configuration version
- credential reference
- credential last validated time
- webhook configuration state
- webhook secret reference
- base endpoint or account reference where required
- default sender or channel identifier where applicable
- rate-limit configuration
- timeout configuration
- retry policy reference
- feature flags
- health state
- last successful operation time
- last failed operation time
- last error category
- created by
- created time
- updated by
- updated time

### 4.2 Integration statuses

Approved statuses:

- draft
- configuring
- validating
- active
- degraded
- paused
- disabled
- failed
- revoked
- archived

### 4.3 Environment handling

Configuration must distinguish:

- local development
- automated test
- staging
- production

Credentials, URLs, webhook secrets, sender identities, and provider account identifiers must not be copied blindly between environments.

Production integration records must never use development test recipients or sample credentials.

### 4.4 Credential storage

- Credentials are never stored in frontend code.
- Secrets are never returned through ordinary API responses.
- Database records store secret references or encrypted values according to the approved secret-management design.
- Logs must redact tokens, passwords, webhook secrets, and sensitive provider payload fields.
- Credential rotation must not require code changes.
- Revoked credentials must be detectable and surfaced.

### 4.5 Configuration changes

Sensitive configuration changes require:

- appropriate permission (`settings.integrations.update`)
- actor identity
- reason where required
- before-and-after audit metadata without exposing secret values
- validation before activation
- rollback or previous-version reference where feasible

## 5. INTEGRATION MANAGEMENT UI

### 5.1 Integration list

Columns:

- integration name
- provider
- category
- status
- environment
- enabled
- health
- last success
- last failure
- updated time

Saved views:

- Active
- Degraded
- Failed
- Needs configuration
- Disabled
- Production
- Staging

### 5.2 Integration detail

Sections:

- summary
- supported capabilities
- current configuration state
- credential state
- webhook state
- health checks
- rate-limit usage where available
- recent operations
- recent failures
- retry queue
- audit history
- documentation notes

Actions depend on permission and state:

- Configure
- Validate
- Activate
- Pause
- Resume
- Rotate credential
- Test connection
- Send test event
- Re-register webhook
- Disable
- View logs

A test action must clearly indicate the environment and target before execution.

## 6. WEBHOOK ARCHITECTURE

### 6.1 Webhook endpoint principles

Inbound webhook endpoints must:

- use provider-specific routes
- authenticate or verify signatures
- reject unsupported methods
- enforce size limits
- parse safely
- preserve raw payload where required for verification or audit
- return provider-appropriate responses quickly
- enqueue non-trivial processing (ARQ)
- deduplicate events
- avoid performing long business workflows synchronously

### 6.2 Webhook receipt fields

Store:

- receipt ID
- provider
- integration ID
- endpoint code
- external event ID
- event type
- signature verification result
- received time
- payload hash
- raw payload storage reference or redacted payload
- headers required for verification
- processing status
- processing attempts
- linked job ID
- linked domain records
- final outcome
- error category
- retention expiry where applicable

### 6.3 Webhook receipt statuses

- received
- verified
- rejected
- duplicate
- queued
- processing
- processed
- partially_processed
- failed_retryable
- failed_permanent
- ignored

### 6.4 Signature verification

- Verification occurs before trusting payload content.
- Exact provider signing rules must be implemented from official provider documentation.
- Secrets are selected by integration and environment.
- Timestamp tolerance must be enforced where the provider supports signed timestamps.
- Invalid signatures produce a safe rejection and security log.
- Development bypasses must never exist in production.

### 6.5 Deduplication

Preferred deduplication order:

1. provider event ID
2. integration ID plus event ID unique constraint
3. deterministic payload hash plus event type and bounded time window where no event ID exists
4. domain-level idempotency key

Duplicate receipts remain visible but do not execute the domain change again.

### 6.6 Webhook processing flow

1. Provider calls endpoint.
2. Endpoint validates request size and method.
3. Signature is verified.
4. Receipt is stored.
5. Duplicate check runs.
6. Processing job is enqueued (ARQ).
7. Endpoint responds promptly.
8. Worker transforms provider payload into an internal event.
9. Domain service validates the action.
10. Transaction commits domain changes and outbox events.
11. Receipt is marked processed or failed.
12. Realtime and notifications are delivered from internal events.

### 6.7 Webhook failure handling

Retryable examples:

- temporary database unavailability
- temporary provider lookup failure
- queue timeout
- transient network error
- lock contention

Permanent examples:

- invalid signature
- unsupported event type
- malformed required fields
- revoked integration
- missing required domain mapping
- event permanently incompatible with current configuration

## 7. OUTBOUND PROVIDER CALLS

### 7.1 Provider request record

Each outbound provider operation should retain:

- operation ID
- integration ID
- operation type
- source domain record
- idempotency key
- destination reference
- provider request ID
- attempt number
- request creation time
- started time
- completed time
- normalized status
- provider status
- response metadata
- error category
- retryable state
- next retry time
- cost metadata where available

Sensitive payload content must be minimized or redacted.

### 7.2 Normalized statuses

- pending
- queued
- sending
- accepted
- sent
- delivered
- read
- completed
- failed_retryable
- failed_permanent
- cancelled
- expired

Not every provider supports every state. Unsupported states must not be fabricated.

### 7.3 Timeout and cancellation

- Connect and total timeouts must be explicit.
- A timed-out request must not be assumed failed if the provider may have accepted it.
- Follow-up reconciliation may be required.
- Cancellation stops unsent queued work where possible.
- Already accepted provider operations remain historically accurate.

## 8. DOMAIN EVENT ARCHITECTURE

### 8.1 Internal domain events

Examples:

- customer.created
- customer.updated
- customer.merged
- lead.created
- lead.stage_changed
- order.created
- order.confirmed
- order.in_preparation
- order.ready
- order.completed
- order.cancelled
- order.refunded
- reservation.created
- reservation.confirmed
- reservation.cancelled
- reservation.no_show
- inventory.low_stock
- inventory.critical_stock
- inventory.adjusted
- campaign.approved
- campaign.scheduled
- campaign.completed
- loyalty.points_earned
- loyalty.points_redeemed
- feedback.received
- complaint.created
- complaint.escalated
- complaint.resolved
- task.assigned
- task.overdue
- report.completed
- report.failed
- integration.degraded

### 8.2 Event envelope

Each event should include:

- event ID
- event type
- event version
- occurred time
- recorded time
- aggregate type
- aggregate ID
- actor type
- actor ID
- correlation ID
- causation ID
- idempotency key where relevant
- payload
- metadata

### 8.3 Event versioning

- Event names remain stable.
- Breaking payload changes require a new event version.
- Consumers must declare supported versions.
- Old events remain processable for the required retention period.
- Event payloads should reference domain IDs rather than duplicate entire records unnecessarily.

## 9. TRANSACTIONAL OUTBOX

### 9.1 Purpose

The transactional outbox prevents a database commit from succeeding while its corresponding asynchronous events are silently lost.

### 9.2 Outbox flow

1. Domain service changes business records inside a transaction.
2. Matching outbox rows are inserted in the same transaction.
3. Transaction commits.
4. Dispatcher claims pending outbox rows.
5. Events are published to internal consumers or ARQ queue jobs.
6. Successful rows are marked published.
7. Failures are retried with bounded backoff.

### 9.3 Outbox fields

- outbox ID
- event ID
- event type
- event version
- aggregate reference
- payload
- metadata
- status
- available time
- attempt count
- locked by
- locked time
- published time
- last error
- created time

### 9.4 Outbox statuses

- pending
- processing
- published
- failed_retryable
- failed_permanent
- cancelled

### 9.5 Claiming and locking

- Workers claim rows atomically.
- Stale locks are recoverable.
- Parallel workers must not publish the same event concurrently.
- Consumer idempotency remains required because at-least-once delivery is expected.

## 10. JOB AND QUEUE ARCHITECTURE

### 10.1 Job types

- immediate asynchronous job
- delayed job
- scheduled recurring job (ARQ cron)
- batch job
- export job
- integration reconciliation job
- campaign execution job
- notification delivery job
- report refresh job
- segment refresh job
- loyalty expiry job
- inventory alert job
- cleanup and retention job

### 10.2 Job fields

- job ID
- job type
- queue name
- priority
- status
- payload reference
- idempotency key
- correlation ID
- scheduled time
- available time
- started time
- completed time
- attempt count
- maximum attempts
- timeout
- locked by
- locked time
- progress
- result reference
- last error category
- last error summary
- created by or system actor
- created time

### 10.3 Job statuses

- scheduled
- pending
- queued
- running
- retry_wait
- succeeded
- failed_permanent
- cancelled
- dead_lettered

### 10.4 Queue separation

ARQ queues should be separated where workload or failure behavior differs materially, for example:

- critical-domain
- communications
- campaigns
- reports
- exports
- integrations
- AI
- maintenance

A large export must not starve urgent order or complaint work.

### 10.5 Priorities

Example priority classes:

- critical
- high
- normal
- low
- maintenance

Priority must not bypass domain authorization or state rules.

## 11. RETRIES AND BACKOFF

### 11.1 Retry classification

Retry only when the failure may succeed later.

Retryable:

- connection timeout
- provider 429
- provider temporary 5xx
- transient database connection failure
- temporary DNS or network failure
- lock timeout

Usually permanent:

- invalid credentials
- invalid destination
- missing required consent
- rejected template
- invalid business state
- unsupported payload
- signature failure
- revoked account

### 11.2 Backoff

- Use exponential backoff with jitter.
- Honor provider retry-after headers.
- Cap maximum delay.
- Cap attempt count.
- Record next retry time.
- Do not retry forever.

### 11.3 Retry safety

Before each retry:

- recheck cancellation
- recheck integration state
- recheck consent where communication is pending
- recheck destination validity
- preserve idempotency key
- avoid double domain mutation

## 12. DEAD-LETTER HANDLING

### 12.1 Dead-letter entry

Store:

- failed job or event reference
- original type
- payload reference
- correlation ID
- failure category
- final error summary
- attempt history
- dead-letter time
- owner or responsible team
- resolution status
- replay eligibility
- replay actor
- replay time

### 12.2 Dead-letter statuses

- new
- investigating
- corrected
- replay_ready
- replayed
- ignored_with_reason
- permanently_closed

### 12.3 Replay rules

Replay requires:

- permission
- corrected root cause
- confirmation that idempotency remains safe
- current integration availability
- current consent where applicable
- audit record

Raw replay must not bypass normal validation.

## 13. AUTOMATION MODEL

### 13.1 Purpose

Automations coordinate predictable restaurant CRM workflows through approved triggers, conditions, delays, and actions.

The system is not a general no-code workflow platform. Automation definitions must come from a supported catalog or controlled backend configuration.

### 13.2 Automation definition fields

- automation code
- name
- description
- module
- status
- trigger type
- trigger configuration
- condition definition
- action sequence
- delay rules
- owner
- approval requirement
- enabled time
- disabled time
- version
- created by
- updated by
- last execution time
- success count
- failure count

### 13.3 Automation statuses

- draft
- in_review
- active
- paused
- disabled
- failed
- archived

### 13.4 Trigger types

- domain_event
- scheduled
- delayed_after_event
- threshold_detected
- manual
- integration_callback

### 13.5 Condition rules

Conditions may evaluate approved fields such as:

- record status
- priority
- ownership
- elapsed time
- consent
- order channel
- customer segment
- loyalty state
- complaint severity
- reservation date
- inventory level
- task due state
- integration health

Conditions must not execute arbitrary user-authored code.

### 13.6 Action types

Supported controlled actions may include:

- create notification
- create task
- assign task
- update a permitted status through domain service
- schedule communication
- create communication draft
- enqueue feedback request
- refresh segment
- generate report
- create escalation
- emit integration reconciliation job
- pause campaign execution on critical failure
- create inventory alert

Consequential financial or customer-facing actions still require their established approvals.

## 14. APPROVED AUTOMATION CATALOG

### 14.1 Order automations

- New valid order creates operational notifications.
- Confirmed order creates preparation workflow records.
- Ready order notifies authorized staff and eligible customer channel where configured.
- Completed eligible order schedules loyalty earning.
- Completed eligible order schedules a feedback request.
- Cancelled or refunded order triggers loyalty and attribution reconciliation.
- Delayed order may create an escalation based on explicit thresholds.

### 14.2 Reservation automations

- New reservation request notifies reservations staff.
- Confirmed reservation schedules reminder jobs.
- Upcoming reservation may create preparation tasks for special requests.
- Cancelled reservation cancels future reminders.
- No-show status updates reporting and customer timeline.
- Completed visit may schedule feedback request.

### 14.3 Customer and lead automations

- New lead creates assignment and follow-up task.
- Lead stage change updates pipeline reporting.
- Overdue lead follow-up creates reminder and escalation.
- Customer merge triggers segment, loyalty, and communication reconciliation.
- Consent withdrawal suppresses pending marketing sends.

### 14.4 Inventory automations

- Stock below reorder threshold creates low-stock alert.
- Stock below critical threshold creates urgent alert.
- Expiring batch creates review task.
- Approved order completion triggers recipe-based consumption where defined by the established inventory workflow.
- Cancellation or correction uses compensating stock movement rather than deleting history.

### 14.5 Campaign automations

- Approved campaign may be scheduled.
- Scheduled campaign resolves audience at execution time.
- Recipient jobs check current consent and suppression.
- Excessive provider failure may pause remaining sends.
- Campaign completion triggers report refresh.
- Refunds or cancellations update campaign attribution.

### 14.6 Feedback and complaint automations

- Low rating creates action-required status.
- Critical language or defined safety concern creates urgent complaint escalation.
- Complaint SLA breach creates manager notification.
- Resolved complaint schedules permitted follow-up.
- Reopened complaint creates new task and preserves previous resolution.

### 14.7 Reporting automations

- Scheduled report generation runs with current permission checks.
- Failed report refresh creates operational notification.
- Export completion notifies requesting user.
- Expired export files are deleted by retention job.

### 14.8 Integration automations

- Repeated credential failure marks integration degraded.
- Revoked credential marks integration failed or disabled.
- Recovered health changes degraded integration back to active after successful validation.
- Webhook processing backlog creates operational alert.
- Dead-letter growth beyond threshold creates system notification.

## 15. SCHEDULED JOBS

Scheduled jobs (ARQ cron) may include:

- reservation reminders
- loyalty expiry processing
- campaign launches
- campaign completion checks
- feedback requests
- segment refreshes
- report refreshes
- scheduled reports
- inventory expiry alerts
- overdue task detection
- complaint SLA checks
- integration health checks
- webhook reconciliation
- cleanup and retention
- audit archival where approved

### 15.1 Scheduling rules

- Store schedules in explicit timezone-aware form.
- Business display uses `Asia/Kolkata`.
- Avoid duplicate scheduling after restart.
- Recurring jobs use stable schedule identifiers.
- A missed run must follow a defined catch-up policy.
- Disabled automations must not create future executions.
- Changes to schedule create audit history.

## 16. REALTIME ARCHITECTURE

### 16.1 Purpose

Realtime features improve coordination by notifying clients of committed backend changes. Realtime is not the source of truth and cannot replace API reads.

### 16.2 Realtime use cases

- order status updates
- reservation status updates
- conversation messages
- assignment changes
- task updates
- notification creation
- campaign progress
- export progress
- report job progress
- integration health changes
- inventory alerts
- complaint escalation
- dashboard invalidation signals

### 16.3 Realtime transport

The implementation uses Supabase Realtime, with authenticated channels and backend-published events.

No alternative realtime service should be added without architecture approval.

### 16.4 Realtime event envelope

- event ID
- event type
- event version
- occurred time
- resource type
- resource ID
- action
- actor summary where permitted
- correlation ID
- payload summary
- refresh hint

Do not send unnecessary full records or sensitive fields.

### 16.5 Channel scopes

Examples:

- user-specific channel
- role or permission-scoped channel where safe
- record-specific channel
- queue or operational-view channel
- job-progress channel

Subscription authorization must be enforced server-side.

### 16.6 Delivery behavior

- Publish only after transaction commit.
- Duplicate events are possible and clients must deduplicate by event ID.
- Ordering is guaranteed only where explicitly implemented.
- Clients must refetch authoritative state after reconnect or sequence gaps.
- Realtime failure must not roll back committed business state.

### 16.7 Client behavior

Clients must:

- authenticate subscription
- subscribe only to permitted channels
- deduplicate events
- update local cache carefully
- refetch when payload is partial
- show reconnect state where relevant
- recover from missed events
- avoid displaying success before API confirmation

## 17. NOTIFICATIONS

### 17.1 Notification channels

- in_app
- email
- whatsapp
- sms where approved

### 17.2 Notification record fields

- notification ID
- type
- severity
- recipient user or role
- source record
- title
- body
- action link
- status
- created time
- read time
- acknowledged time
- delivery channels
- delivery attempt references
- deduplication key
- expiry time

### 17.3 Notification statuses

- pending
- delivered
- read
- acknowledged
- dismissed
- expired
- failed

### 17.4 Deduplication

Notifications for repeated identical conditions must use stable deduplication keys, for example:

- same overdue task and escalation level
- same integration failure window
- same inventory item and threshold state
- same complaint SLA breach

### 17.5 Notification preferences

User preferences may control non-critical channels. Critical operational or security notifications may remain mandatory for authorized roles.

Preferences never override marketing consent rules for customer communications.

## 18. COMMUNICATION INTEGRATIONS

### 18.1 Shared requirements

- approved templates where provider rules require them
- consent and communication-basis checks
- normalized recipient addresses
- opt-out handling
- delivery callback processing
- retry classification
- provider rate limits
- message history linkage
- safe content rendering
- attachment validation

### 18.2 WhatsApp

The WhatsApp integration must support only capabilities actually implemented and approved (WhatsApp Cloud API — see `TOOLS.md` §10.1).

Required controls:

- approved business account configuration
- provider webhook verification
- message template management where required
- conversation-window rules
- inbound message deduplication
- outbound idempotency
- opt-out processing
- delivery status normalization
- media validation
- human handoff visibility

No placeholder provider name or invented account detail may be treated as final.

### 18.3 Email

Required controls:

- verified sender configuration
- domain authentication state where applicable
- bounce handling
- complaint handling where supported
- unsubscribe processing for marketing
- template versioning
- attachment limits
- provider message ID storage
- delivery state normalization

### 18.4 SMS

SMS remains disabled unless an approved provider and use case are defined in `TOOLS.md`.

The UI must not imply SMS is available before configuration.

## 19. WEBSITE AND FORM INTEGRATIONS

### 19.1 Supported inbound sources

- contact form
- reservation form
- lead form
- feedback form
- customer support chat
- website order flow where implemented

### 19.2 Form security

- server-side validation
- rate limiting
- spam controls
- CSRF protection where applicable
- origin validation where appropriate
- payload-size limits
- duplicate submission controls
- safe attachment handling
- consent capture with version and source

### 19.3 Inbound form flow

1. Website submits to approved API endpoint.
2. Backend validates and normalizes data.
3. Duplicate and abuse checks run.
4. Domain record is created transactionally.
5. Outbox event is stored.
6. Staff notification and realtime update are produced.
7. Customer acknowledgement is sent only when configured and permitted.

## 20. PAYMENT AND FINANCIAL CALLBACKS

Payment integration is optional and only active when explicitly implemented.

If enabled:

- provider credentials remain secret
- webhooks are signature-verified
- amount and currency are validated against the authoritative order (integer minor units)
- external transaction IDs are unique
- payment state transitions are controlled
- duplicate callbacks are idempotent
- browser redirects never become proof of payment
- refunds require approved workflows
- reconciliation jobs detect missing callbacks

No payment provider may be selected or represented as final through dummy data.

## 21. FILE STORAGE, EXPORTS, AND ATTACHMENTS

### 21.1 Storage rules

- files are private by default
- metadata is stored in PostgreSQL
- object storage (Supabase Storage) holds bytes
- access uses short-lived signed URLs
- uploads are validated by size and type
- malicious file handling follows the security design
- expired generated exports are deleted by retention jobs

### 21.2 Export jobs

- permission checked at request time
- large exports run asynchronously (ARQ)
- generated file linked to requesting user
- completion notification created
- permission checked again before download where required
- file expiry recorded
- generation and download audited where sensitive

## 22. AI INTEGRATION BOUNDARIES

AI integration follows `GROWTH_AND_INTELLIGENCE.md` and is implemented and credentialed only in Phase 14.

- AI is advisory.
- Core CRM remains usable without AI.
- Context is permission-scoped and minimized.
- Prompt templates are versioned.
- Structured output is validated.
- Customer-facing content requires review.
- Provider outages degrade gracefully.
- Cost and rate controls are applied.
- No RAG, embeddings, vector search, or pgvector are introduced.
- AI cannot execute arbitrary tools or database queries.

## 23. INTEGRATION HEALTH AND RECONCILIATION

### 23.1 Health states

- unknown
- healthy
- degraded
- unhealthy
- disabled

### 23.2 Health signals

- credential validation
- successful recent request
- webhook delivery activity
- provider rate-limit status
- repeated error rate
- queue backlog
- callback delay
- reconciliation mismatch

### 23.3 Reconciliation jobs

Reconciliation may compare:

- pending outbound message records versus provider state
- accepted payment records versus provider transactions
- scheduled campaign recipients versus send attempts
- webhook receipt sequence versus provider history where available
- export job state versus stored file

Reconciliation creates corrective jobs or alerts. It must not silently rewrite financial history.

## 24. OBSERVABILITY

### 24.1 Required logs

- integration operation start and outcome
- webhook verification outcome
- job start, retry, success, and failure
- outbox publication
- automation execution
- realtime publish failure
- provider rate-limit response
- dead-letter creation
- reconciliation mismatch

### 24.2 Correlation

Requests, jobs, events, provider operations, and resulting domain changes should share correlation identifiers.

### 24.3 Metrics

- jobs queued
- jobs running
- job success rate
- retry rate
- dead-letter count
- queue latency
- webhook volume
- webhook verification failures
- duplicate webhook count
- provider request latency
- provider failure rate
- realtime publish failures
- notification delivery rate
- integration health by provider
- automation success rate

### 24.4 Alerts

- critical queue backlog
- repeated worker failure
- growing dead-letter queue
- invalid webhook signature spike
- credential revocation
- provider outage
- campaign send failure spike
- payment reconciliation mismatch where applicable
- realtime service degradation

## 25. SECURITY REQUIREMENTS

- All integration management is permission-controlled (`settings.integrations.update`).
- Secrets are never exposed in UI or logs.
- Webhooks are verified.
- Outbound callbacks use HTTPS.
- Provider URLs are allowlisted where appropriate.
- SSRF protections apply to configurable URLs.
- Attachments and external media are untrusted.
- Rate limits protect public endpoints.
- Replay attacks are mitigated where provider signatures support timestamps.
- Automation actions use backend domain services.
- Realtime subscriptions are authenticated and authorized.
- Audit history exists for configuration and consequential automation changes.
- Production cannot use test bypasses.

## 26. PERFORMANCE REQUIREMENTS

- Webhook endpoints acknowledge quickly.
- Long work runs asynchronously (ARQ).
- Queue consumers use bounded concurrency.
- Critical queues are isolated from bulk queues.
- Backpressure prevents uncontrolled memory growth.
- Realtime payloads are small.
- Campaign recipients are processed in batches.
- Report and export jobs are bounded.
- Provider rate limits are respected centrally.
- Integration list and job history are paginated.
- Logs and webhook payload retention are bounded.

## 27. FAILURE AND RECOVERY SCENARIOS

The system must handle:

- worker restart during a job
- queue connection loss
- database transaction rollback
- event published more than once
- provider accepts request but response times out
- callback arrives before outbound response is stored
- callback arrives multiple times
- credentials expire during campaign
- consent withdrawn while message is queued
- integration disabled while jobs remain pending
- webhook backlog after outage
- realtime disconnect
- scheduled job missed during deployment
- dead-letter replay after root-cause correction
- export generated but notification failed
- report delivery recipient loses permission

Each scenario requires a deterministic recovery path and tests.

## 28. TESTING REQUIREMENTS

Automated tests must cover:

- integration status transitions
- secret redaction
- webhook signature success and failure
- duplicate webhook handling
- webhook processing retry
- provider timeout ambiguity
- outbound idempotency
- rate-limit handling
- outbox atomicity
- outbox duplicate publication
- job locking and stale-lock recovery
- retry classification
- dead-letter creation and safe replay
- scheduled job deduplication
- consent recheck before send
- automation condition evaluation
- automation permission enforcement
- realtime authorization
- reconnect and missed-event recovery
- notification deduplication
- export permission recheck
- integration health degradation and recovery
- provider outage isolation
- no core workflow dependency on AI

## 29. DEFINITION OF DONE

The integration, automation, or realtime capability is complete only when:

- behavior matches this document
- data and APIs match `DATABASE_AND_API.md`
- architecture matches `ARCHITECTURE_AND_TECH_STACK.md`
- business behavior matches the core, operations, and growth documents
- provider decisions match `TOOLS.md`
- dummy data is limited to test fixtures
- credentials and production URLs are not invented
- permissions are backend-enforced
- webhook verification is implemented
- idempotency is tested
- retries are bounded
- dead-letter handling exists
- observability exists
- failure recovery is documented and tested
- realtime remains non-authoritative
- provider outage does not break unrelated CRM workflows
- UI includes loading, empty, degraded, disabled, and failure states
- audit history exists for sensitive actions

## 30. FINAL IMPLEMENTATION COMMAND

Build RKPR Restaurant CRM integrations, automations, and realtime capabilities as reliable backend infrastructure, not decorative UI or a generic workflow builder. Use verified provider contracts, secure secrets, signed webhooks, idempotent ARQ jobs, the transactional outbox, bounded retries, dead-letter recovery, permission-aware realtime channels, and clear integration health. Automations must reuse authoritative domain services and must never bypass consent, approvals, financial rules, state machines, or audit requirements. Preserve established RKPR dummy records only for development fixtures, and never invent providers, credentials, production URLs, security rules, or critical architecture decisions.
