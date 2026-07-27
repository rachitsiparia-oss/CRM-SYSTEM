# RKPR RESTAURANT CRM — SECURITY, PERFORMANCE, AND QUALITY

## 1. DOCUMENT PURPOSE

This document defines the production security model, performance standards, reliability controls, quality gates, testing requirements, observability expectations, operational safeguards, incident response, backup and recovery rules, and release acceptance criteria for the RKPR Restaurant CRM.

It must remain consistent with `PROJECT_PLAN.md`, `ARCHITECTURE_AND_TECH_STACK.md`, `DATABASE_AND_API.md`, `CORE_CRM_MODULES.md`, `OPERATIONS_MODULES.md`, `GROWTH_AND_INTELLIGENCE.md`, and `INTEGRATIONS_AUTOMATIONS_REALTIME.md`.

This document is authoritative for:

- authentication and session security
- backend authorization
- capability-based permissions
- secret management
- data protection
- API security
- database security
- file and attachment security
- webhook and integration security
- frontend security
- infrastructure security
- logging and audit safety
- privacy and retention
- availability and resilience
- performance budgets
- scalability expectations
- observability and alerting
- automated testing
- quality gates
- CI/CD release controls
- backup and disaster recovery
- incident response
- production readiness

Dummy information is permitted only for development fixtures, test users, synthetic performance workloads, mock provider responses, and security test cases. Important decisions such as authentication design, authorization behavior, encryption, security controls, infrastructure, provider selection, backup policy, performance budgets, retention, incident severity, or release gates must never be invented from dummy assumptions.

## 2. CORE SECURITY PRINCIPLES

### 2.1 Backend enforcement

All consequential security checks are enforced in the backend.

The frontend may hide or disable unavailable actions for usability, but this is not authorization.

The backend must verify:

- authenticated identity
- active account state
- required capability (from the single canonical registry in `DATABASE_AND_API.md` §4.4)
- record visibility
- ownership or assignment where relevant
- business-state eligibility
- approval requirements
- rate limits
- idempotency
- current consent where communication is involved
- current integration state where provider action is involved

### 2.2 Least privilege

Users, services, database roles, workers, storage policies, CI jobs, and integrations receive only the permissions required for their current responsibility.

No shared super-admin credential may be used by ordinary frontend or worker operations.

### 2.3 Secure by default

Default behavior must favor safety:

- private files
- denied access unless explicitly granted
- disabled unconfigured integrations
- no public database access
- no exposed secrets
- no permissive CORS wildcard in production
- no test bypasses in production
- no automatic customer-facing AI actions
- no destructive action without confirmation and permission
- no broad realtime subscriptions

### 2.4 Defense in depth

Security must not depend on one control.

Examples:

- frontend validation plus backend validation plus database constraints
- authenticated session plus capability check plus record-scope check
- webhook signature verification plus timestamp tolerance plus deduplication
- file extension checks plus MIME checks plus signature checks plus malware scanning
- API rate limiting plus abuse detection plus bounded payload size
- secure cookies plus CSRF protection plus origin validation where applicable

### 2.5 Traceability

Sensitive and consequential actions require an attributable audit trail.

Audit history must identify:

- actor
- action
- target record
- timestamp
- request or correlation ID
- before-and-after summary where appropriate
- reason where required
- approval reference where required
- source channel
- outcome

### 2.6 Graceful degradation

Failure of an optional subsystem must not compromise security or corrupt core CRM state.

Examples:

- AI outage does not block CRM access
- email outage does not block order creation
- realtime outage does not corrupt stored records
- export failure does not erase source data
- monitoring outage does not bypass authorization

## 3. IDENTITY AND AUTHENTICATION

### 3.1 Identity source

Supabase Auth remains the approved identity source as defined in the architecture documents.

The CRM must use verified user identity from valid server-side session or token validation.

### 3.2 Authentication requirements

- unique user identity
- verified email where required
- secure password policy where password authentication is enabled
- supported recovery flow
- account disable and revoke capability
- short-lived access credentials
- controlled refresh flow
- session invalidation after sensitive account changes
- audit history for sign-in and security changes

### 3.3 Session handling

Preferred browser session behavior:

- secure HTTP-only cookies
- `Secure` enabled in production
- appropriate `SameSite` policy
- bounded session lifetime
- refresh rotation where supported
- no tokens in localStorage when avoidable
- no secrets in URL query strings
- session revocation support
- logout invalidates local and server-side session state as applicable

### 3.4 Login protection

The login flow must support:

- generic error responses that avoid account enumeration
- rate limiting by IP and account identifier
- progressive delay or lockout controls
- suspicious-attempt logging
- bot and abuse protection where needed
- secure recovery tokens
- recovery-token expiry
- one-time use of recovery links

### 3.5 Multi-factor authentication

MFA should be available or required for highly privileged roles when supported by the final identity configuration.

At minimum, the architecture must not block future MFA enforcement.

### 3.6 Account states

Approved account states:

- invited
- active
- suspended
- disabled
- locked
- archived

Disabled, suspended, locked, or archived users must not receive active CRM access.

### 3.7 Service identities

Workers and backend services must use service identities or server-side credentials scoped to their purpose.

Service credentials must never be exposed to browser clients.

## 4. AUTHORIZATION AND PERMISSIONS

### 4.1 Capability model

Authorization is capability-based, using the single canonical permission-code registry defined in `DATABASE_AND_API.md` §4.4: lowercase, dot-separated, domain first, action or sub-action after the domain.

Representative capability families (the complete registry is represented in code from `DATABASE_AND_API.md` §4.4 and tested for uniqueness — this document does not define a second, competing list):

- `dashboard.view`
- `customers.view`, `customers.create`, `customers.update`, `customers.merge`, `customers.export`
- `leads.view`, `leads.create`, `leads.update`, `leads.assign`, `leads.transition`
- `orders.view`, `orders.create`, `orders.update`, `orders.transition`, `orders.discount.apply`, `orders.cancel.request`, `orders.cancel.approve`, `orders.refund.request`, `orders.refund.approve`
- `menu.view`, `menu.create`, `menu.update`, `menu.archive`, `menu.restore`, `menu.categories.manage`, `menu.modifiers.manage`, `menu.images.manage`
- `inventory.view`, `inventory.items.create`, `inventory.receipts.create`, `inventory.receipts.post`, `inventory.adjustments.create`, `inventory.adjustments.approve`, `inventory.transfers.create`, `inventory.transfers.post`, `inventory.counts.approve`, `inventory.balances.rebuild` (26 codes total — see `DATABASE_AND_API.md` §9.8 for the full list)
- `reservations.view`, `reservations.create`, `reservations.update`, `reservations.approve`, `reservations.transition`
- `communications.view`, `communications.send`
- `campaigns.view`, `campaigns.create`, `campaigns.approve`, `campaigns.send`
- `loyalty.view`, `loyalty.adjust`
- `feedback.view`, `complaints.manage`
- `staff.view`, `staff.manage`, `staff.hr_sensitive.read`
- `roles.view`, `roles.manage`
- `reports.view`, `reports.export`
- `settings.view`, `settings.manage`, `settings.integrations.update`
- `audit.view`
- `system.health_view`

### 4.2 Permission evaluation

Every protected backend action must evaluate:

1. authenticated user
2. active user status
3. required capability
4. record-level visibility
5. assignment or ownership restrictions where defined
6. business-state restrictions
7. required approval
8. data sensitivity restrictions

### 4.3 High-risk actions

High-risk actions require stronger controls, which may include:

- explicit confirmation
- recent authentication
- reason entry
- dual approval
- limited role access
- audit record
- notification to an authorized manager

High-risk examples:

- refunds (`orders.refund.approve`)
- large discounts (`orders.discount.apply`)
- customer merges (`customers.merge`)
- loyalty balance adjustments (`loyalty.adjust`)
- staff access changes (`staff.manage`, `roles.manage`)
- integration credential changes (`settings.integrations.update`)
- bulk exports (`*.export`)
- destructive data actions
- policy publication
- replay of dead-lettered financial events

### 4.4 Privilege escalation prevention

A user must not be able to:

- assign themselves capabilities they do not possess
- modify their own role without authorization
- approve their own restricted action when separation is required
- change record ownership to bypass access rules
- call hidden backend endpoints directly to bypass UI restrictions

### 4.5 Authorization testing

Every protected route requires tests for:

- authorized role succeeds
- unauthorized role is denied
- unauthenticated request is denied
- disabled user is denied
- wrong record scope is denied
- hidden UI does not replace backend enforcement

## 5. SECRET MANAGEMENT

### 5.1 Secret categories

- database credentials
- Supabase service credentials
- JWT or session secrets
- provider API keys
- webhook secrets
- encryption keys
- email or WhatsApp credentials
- observability credentials
- deployment tokens
- CI secrets

### 5.2 Storage rules

- secrets never appear in source control
- secrets never appear in public environment variables
- secrets never appear in frontend bundles
- secrets never appear in logs
- secrets are environment-specific
- production secrets are not reused in development
- credentials can be rotated without code changes
- access to secrets is restricted and auditable

### 5.3 Rotation

Credential rotation procedures must define:

- owner
- rotation frequency where required
- replacement process
- overlap period if supported
- validation
- rollback
- revocation
- post-rotation monitoring

### 5.4 Redaction

Logs, audit metadata, support exports, screenshots, and error traces must redact:

- passwords
- access tokens
- refresh tokens
- session cookies
- API keys
- authorization headers
- webhook signatures
- database URLs
- private customer content beyond operational need

## 6. DATA PROTECTION

### 6.1 Data classification

Suggested data classes:

- Public: public menu and approved public business information
- Internal: operational configurations and non-sensitive internal notes
- Confidential: customer contact data, staff data, supplier agreements, campaign records
- Restricted: authentication data, financial records, security logs, integration credentials, sensitive HR records

### 6.2 Data minimization

Collect and retain only data required for operational, legal, analytical, or customer-service purposes.

Do not copy complete customer or staff records into unrelated tables, events, logs, AI prompts, or realtime messages.

### 6.3 Encryption

- HTTPS/TLS for data in transit
- provider-supported encryption at rest
- secure storage encryption
- sensitive secret encryption or secret references
- no plaintext credentials in database fields

### 6.4 Sensitive field handling

Sensitive fields require:

- restricted read access
- restricted exports
- masking where full values are unnecessary
- controlled audit visibility
- retention policy
- secure deletion workflow where applicable

### 6.5 Data integrity

Use:

- database constraints
- foreign keys
- check constraints
- unique constraints
- immutable ledgers for financial and loyalty history
- version or concurrency controls
- idempotency keys
- transaction boundaries

### 6.6 Data deletion

Deletion must distinguish:

- ordinary soft deletion
- archival
- legal retention
- anonymization
- irreversible purge

Hard deletion of sensitive or historically important data requires explicit authorization and documented policy.

## 7. API SECURITY

### 7.1 Request validation

Every endpoint must validate:

- content type
- payload size
- schema
- required fields
- field lengths
- enum values
- identifier format
- pagination bounds
- filter allowlist
- sort allowlist
- file constraints

### 7.2 Response safety

Responses must not expose:

- internal stack traces
- SQL details
- secret values
- unauthorized fields
- hidden record existence
- internal provider credentials
- unrestricted audit payloads

### 7.3 Rate limiting

Rate limits should be applied based on risk and endpoint type.

Rate-limit dimensions may include:

- authenticated user
- IP address
- integration
- API key where applicable
- destination identifier
- route group

Stricter limits apply to:

- login
- password recovery
- public forms
- file upload
- export creation
- bulk operations
- messaging
- webhook endpoints where abuse risk exists

### 7.4 Idempotency

Mutating operations that may be retried require idempotency where appropriate, including:

- order creation
- payment callbacks
- webhook processing
- campaign recipient sends
- loyalty transactions
- inventory deductions
- report generation
- exports
- customer imports

### 7.5 CORS

Production CORS must use an explicit allowlist of approved origins.

Do not use wildcard origins with credentials.

### 7.6 CSRF

Cookie-authenticated state-changing requests require CSRF protection appropriate to the final session design.

### 7.7 Security headers

Production responses should include appropriate headers such as:

- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options
- Referrer-Policy
- frame-ancestor restrictions
- Permissions-Policy where appropriate

### 7.8 Error model

The API must return stable, sanitized errors with:

- error code
- safe message
- field errors where applicable
- request ID
- no secret or stack-trace disclosure

## 8. DATABASE SECURITY

### 8.1 Connectivity

- database is not publicly exposed beyond approved provider access
- TLS is used
- credentials are environment-specific
- pooled connections are bounded
- application and migration credentials may be separated

### 8.2 Least-privilege database roles

Database roles should separate where feasible:

- runtime application
- migrations
- read-only reporting
- operational support
- backup or maintenance

### 8.3 Query safety

- parameterized queries
- ORM or query-builder safe bindings (SQLAlchemy 2.x with psycopg 3)
- no string-built SQL from untrusted input
- allowlisted dynamic sort and filter fields
- bounded queries
- statement timeouts where appropriate

### 8.4 Migration safety

Migrations must be:

- version-controlled (Alembic)
- deterministic
- reviewed
- tested against realistic data
- backward-compatible during rolling deployment where needed
- protected against accidental destructive execution
- accompanied by rollback or recovery procedure

### 8.5 Row-level security

The current product is a single-resort deployment, not multi-tenant.

Tenant-based RLS is not required.

RLS may still be used where it provides specific protection for direct Supabase Storage or approved realtime access, but it must not create a second conflicting authorization model.

Every table must still have RLS **enabled with zero policies**, regardless of the above — added during Phase 3 after Supabase's Table Editor flagged every table as "Unrestricted." Without this, every table is reachable through Supabase's auto-generated REST API (PostgREST) using the public `anon` key shipped in the browser bundle, completely bypassing FastAPI's authorization layer, regardless of whether the frontend is ever intended to call that path directly. RLS-enabled-with-no-policies denies all PostgREST access by default without requiring a second, business-rule-shaped authorization model (no policies to write or keep in sync with `app.permissions`). `apps/api`'s own connection is unaffected: it connects as the table-owning `postgres.<project-ref>` role over a direct connection, not through PostgREST, and table owners bypass RLS unless `FORCE ROW LEVEL SECURITY` is also set — it is not. Every new migration that creates a table must include `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY` in the same migration.

### 8.6 Audit integrity

Audit records must not be editable by ordinary business users.

Sensitive audit access requires the `audit.view` permission.

## 9. FILE AND ATTACHMENT SECURITY

### 9.1 Upload validation

Validate:

- file size
- extension
- MIME type
- file signature
- allowed category
- filename safety
- upload count
- record ownership

### 9.2 Storage

- private buckets by default
- server-generated paths
- no user-controlled traversal paths
- short-lived signed access
- metadata in PostgreSQL
- bytes in object storage

### 9.3 Malware handling

Files that require scanning follow this flow:

1. upload to quarantine
2. validate metadata and signature
3. malware scan
4. mark clean, rejected, or failed
5. move or expose only clean files
6. record scan status

### 9.4 Image processing

Image processing must protect against:

- decompression bombs
- malicious metadata
- unsupported formats
- excessive dimensions
- unsafe SVG content

### 9.5 Download authorization

Signed URLs are created only after backend permission checks.

A copied or expired URL must not provide indefinite access.

## 10. WEBHOOK AND INTEGRATION SECURITY

### 10.1 Inbound webhooks

- provider-specific endpoint
- signature verification
- timestamp tolerance where available
- raw body preservation where required
- replay protection
- payload size limits
- deduplication
- quick acknowledgement
- asynchronous processing (ARQ)

### 10.2 Outbound integrations

- HTTPS only
- explicit timeouts
- bounded retries
- provider URL allowlisting where configurable
- SSRF protections
- secret redaction
- idempotency
- destination validation

### 10.3 Provider failure isolation

Integration failure must not expose secrets, corrupt domain state, or block unrelated workflows.

### 10.4 Test modes

Test actions must clearly show:

- environment
- provider
- destination
- data being sent

Production test actions require authorization and must not accidentally contact arbitrary recipients.

## 11. FRONTEND SECURITY

### 11.1 Rendering safety

- escape untrusted content
- sanitize rich text
- avoid unsafe HTML injection
- prevent script execution from customer messages or knowledge content
- treat external URLs as untrusted

### 11.2 Client state

Do not store sensitive authoritative data longer than needed in browser state.

Do not rely on client state for:

- permission decisions
- financial totals
- order status truth
- payment confirmation
- inventory truth
- audit history

### 11.3 Dependency safety

Frontend dependencies must be:

- justified
- actively maintained
- locked through pnpm (`pnpm-lock.yaml`)
- scanned for vulnerabilities
- reviewed before major version upgrades

### 11.4 Build safety

Production builds must not include:

- source secrets
- debug credentials
- test bypasses
- development endpoints
- verbose stack traces
- unapproved analytics scripts

## 12. INFRASTRUCTURE SECURITY

### 12.1 Environments

Required separation:

- local development
- automated test
- staging
- production

Each environment has separate credentials and data.

### 12.2 Network and platform controls

- HTTPS enforced
- private or controlled database connectivity
- restricted administrative access
- environment-level secret controls
- platform logs protected
- unused services disabled
- service health endpoints do not reveal secrets

### 12.3 CI/CD permissions

CI jobs receive only required permissions.

Production deployment credentials must not be available to untrusted pull-request jobs.

### 12.4 Branch protection

Production-bound branches should require:

- pull request
- passing CI
- review
- no unresolved critical security findings
- no failing migration checks
- no failing production build

### 12.5 Dependency and image scanning

Scan:

- npm dependencies (pnpm audit)
- Python dependencies (uv-managed)
- container images where used
- leaked secrets
- known vulnerable packages

Critical findings block release unless explicitly reviewed and accepted with documented reason.

## 13. LOGGING, AUDIT, AND PRIVACY SAFETY

### 13.1 Structured logging

Logs should include (via structlog):

- timestamp
- service
- environment
- severity
- request ID
- correlation ID
- route or operation
- user or service actor reference where safe
- duration
- outcome
- error category

### 13.2 Log minimization

Do not log complete:

- passwords
- tokens
- headers containing credentials
- customer message bodies unless operationally necessary
- payment details
- sensitive HR records
- file contents
- full AI prompts containing private data

### 13.3 Audit versus logs

Audit history records business and security actions.

Application logs support technical diagnosis.

Neither should be used as a substitute for the other.

### 13.4 Retention

Retention periods must be documented by data category and implemented through scheduled cleanup or archival jobs.

Retention must consider:

- operational needs
- legal obligations
- privacy
- storage cost
- investigation needs

## 14. PERFORMANCE OBJECTIVES

### 14.1 General principle

Performance must be designed and measured, not assumed.

Targets should be validated in staging with realistic data volumes and concurrency, using k6.

### 14.2 User-facing API targets

Recommended initial targets under normal production load:

- simple reads: p95 under 500 ms
- standard list and filter operations: p95 under 800 ms
- ordinary mutations: p95 under 1 second, excluding third-party calls
- dashboard summary endpoints: p95 under 1.5 seconds
- authentication-dependent page shell usable quickly without waiting for all secondary widgets

These are engineering targets, not guarantees for external-provider operations.

### 14.3 Frontend performance budgets

- route-level code splitting
- no unnecessary client components
- avoid oversized initial JavaScript bundles
- lazy-load heavy charts and editors
- optimize images
- use pagination or virtualization for long lists
- avoid unbounded DOM rendering
- cancel stale requests
- reuse TanStack Query cache appropriately

### 14.4 Core Web Vitals

Public or customer-facing pages should target good Core Web Vitals.

Internal CRM pages should still prioritize responsive interaction, stable layout, and fast navigation.

### 14.5 Database query targets

- indexed common filters
- bounded pagination
- no N+1 queries
- no unbounded scans in interactive routes
- query-plan review for slow endpoints
- statement timeouts for risky reporting queries where appropriate
- summary tables only when justified

### 14.6 Background workloads

- large exports run asynchronously (ARQ)
- campaigns process recipients in bounded batches
- reports use ARQ workers
- file processing uses ARQ workers
- maintenance jobs do not starve critical queues
- queue concurrency is bounded per workload

### 14.7 External provider calls

External calls must use:

- connect timeout
- total timeout
- retry classification
- circuit or degradation behavior where useful
- asynchronous execution for non-immediate workflows

## 15. SCALABILITY

### 15.1 Scaling model

The application remains a modular monolith with independently scalable API and worker processes.

### 15.2 Horizontal scaling

API instances should remain stateless except for approved external state in PostgreSQL, Redis, or storage.

Workers scale independently by queue type (ARQ).

### 15.3 Database-first optimization

Before introducing new infrastructure:

1. inspect query plans
2. add appropriate indexes
3. reduce payloads
4. remove N+1 queries
5. cache stable expensive results
6. use summary tables where justified
7. separate long-running jobs

### 15.4 Avoid premature complexity

Do not introduce Kafka, Kubernetes, Elasticsearch, or microservices without demonstrated need and architecture approval.

## 16. CACHING

### 16.1 Cache use cases

Cache only data where temporary staleness is acceptable, for example:

- reference data
- low-risk dashboard summaries
- public menu data
- permission metadata with safe invalidation
- expensive non-financial aggregates

### 16.2 Cache rules

- PostgreSQL remains authoritative
- TTL is explicit
- invalidation strategy is defined
- cache keys are versioned
- sensitive data is minimized
- cache failure falls back safely
- no financial or order truth depends solely on cache

### 16.3 Cache stampede prevention

Use bounded locks, stale-while-revalidate, or request coalescing where justified.

## 17. REALTIME PERFORMANCE AND SAFETY

- subscribe only to necessary channels
- avoid subscription per table row
- small event payloads
- publish after transaction commit
- client deduplication by event ID
- refetch after reconnect
- server-side subscription authorization
- no sensitive full-record broadcast
- graceful fallback to API polling or refresh

## 18. AVAILABILITY AND RESILIENCE

### 18.1 Health checks

- liveness endpoint
- readiness endpoint
- database connectivity health
- Redis connectivity where required
- worker health
- queue backlog health
- integration health shown separately

### 18.2 Timeouts

Every network and long-running operation requires a timeout.

### 18.3 Retries

Retries are bounded and only used for retryable failures.

### 18.4 Circuit and degradation behavior

Repeated external-provider failures should mark the integration degraded and reduce repeated pressure.

### 18.5 Failure isolation

Separate ARQ queues and service boundaries prevent bulk exports, campaigns, or AI work from starving critical operational workflows.

## 19. OBSERVABILITY

### 19.1 Required signals

- request count
- request latency
- error rate
- database latency
- slow queries
- connection-pool use
- worker throughput
- queue latency
- retry rate
- dead-letter count
- integration failure rate
- webhook verification failures
- realtime publish failures
- cache hit rate
- export duration
- report duration
- authentication failures
- authorization denials

### 19.2 Error tracking

Sentry remains the approved error-tracking platform from the architecture stack.

Errors should include safe context and correlation IDs without secrets.

### 19.3 Alerting

Alerts should exist for:

- production API outage
- database unavailability
- critical error-rate spike
- authentication failure spike
- authorization anomaly
- worker failure
- critical queue backlog
- dead-letter growth
- backup failure
- storage failure
- invalid webhook signature spike
- repeated integration credential failure
- high latency regression
- disk or quota risk where measurable

### 19.4 Alert quality

Alerts must be actionable and avoid duplicate noise.

Each alert should define:

- severity
- owner
- condition
- notification route
- runbook
- recovery condition

## 20. TESTING STRATEGY

### 20.1 Test pyramid

Use a balanced suite of:

- unit tests
- integration tests
- API tests
- database tests
- contract tests
- component tests
- end-to-end tests
- security tests
- performance tests (k6)

### 20.2 Backend tests

Pytest-based tests should cover:

- domain rules
- state transitions
- validation
- permissions
- database constraints
- transactions
- idempotency
- concurrency
- migrations
- ARQ worker retries
- webhook verification
- integration adapters
- audit creation

### 20.3 Frontend tests

Vitest and React Testing Library should cover:

- component behavior
- permission states
- form validation
- loading states
- empty states
- error states
- accessibility behavior
- cache updates
- safe rendering

### 20.4 End-to-end tests

Playwright should cover critical user journeys such as:

- login and logout
- customer creation and update
- lead creation and stage change
- order creation and completion
- reservation creation and confirmation
- inventory adjustment with permission
- complaint escalation
- campaign approval boundary
- export request and completion
- integration degraded state

### 20.5 Security testing

Automated and manual tests should cover:

- broken access control
- IDOR attempts
- injection
- XSS
- CSRF
- authentication abuse
- session fixation or reuse
- rate-limit bypass
- file upload abuse
- path traversal
- SSRF
- webhook replay
- signature bypass
- secret leakage
- unsafe redirects
- privilege escalation
- insecure direct storage access

### 20.6 Performance testing

Use k6 to test:

- common list endpoints
- dashboard loads
- order creation concurrency
- inventory updates
- reservation availability
- campaign batching
- export generation
- queue backlog recovery
- realtime reconnect behavior

## 21. TEST DATA AND ENVIRONMENTS

### 21.1 Dummy-data policy

Use the same established RKPR sample records across documents and fixtures, including the canonical 65-person dummy staff set.

Dummy data must not define:

- real credentials
- real production URLs
- real provider decisions
- security thresholds presented as legal requirements
- actual staff access without approval

### 21.2 Test isolation

Tests must not depend on production data or production providers.

### 21.3 Determinism

Tests should be reproducible and control time, randomness, and external responses where needed.

### 21.4 Cleanup

Automated tests clean up temporary records, files, jobs, and provider mocks.

## 22. CODE QUALITY

### 22.1 General standards

- clear module boundaries
- strict typing
- consistent naming
- small focused functions
- explicit error handling
- no duplicated business rules
- no hidden side effects
- no silent exception swallowing
- documented public interfaces

### 22.2 Python quality

- Python 3.12
- typed functions
- Pydantic schemas
- SQLAlchemy 2.x patterns with psycopg 3
- **Ruff** for linting and formatting
- **mypy** for static type checking
- no synchronous blocking calls in async request paths

### 22.3 TypeScript quality

- strict TypeScript
- no unjustified `any`
- typed API client (`packages/api-client`)
- shared contracts where approved (`packages/contracts`)
- exhaustive handling of important states
- no direct database calls from frontend

### 22.4 Code review

Review should verify:

- business correctness
- security
- performance
- test coverage
- migration safety
- error handling
- observability
- consistency with project documents

## 23. ACCESSIBILITY AND UX QUALITY

The CRM should meet practical accessibility expectations:

- keyboard navigation
- visible focus
- semantic labels
- accessible forms
- sufficient contrast
- readable error messages
- screen-reader-friendly status updates
- no color-only meaning
- reduced-motion support where appropriate

Quality includes:

- consistent loading states
- clear empty states
- actionable errors
- confirmation for destructive actions
- optimistic UI only where safe
- no false success before backend confirmation

## 24. CI QUALITY GATES

Every pull request should run:

- formatting check (Ruff, Prettier/ESLint)
- linting (Ruff, ESLint)
- static type checking (mypy, strict TypeScript)
- unit tests
- integration tests where feasible
- migration validation
- frontend build
- backend import or startup validation
- dependency vulnerability scan
- secret scan

Release is blocked by:

- failing tests
- failing production build
- migration failure
- unresolved critical vulnerability
- detected secret leakage
- missing required environment configuration
- incompatible API contract change without versioning

## 25. RELEASE PROCESS

### 25.1 Pre-release

- approved pull request
- CI green
- migration reviewed
- staging validation
- critical journeys tested
- monitoring ready
- rollback plan available
- release notes prepared

### 25.2 Deployment order

Deployment order must account for backward compatibility between database, API, workers, and frontend.

### 25.3 Post-release validation

Verify:

- API health
- dashboard load
- login
- database migrations
- worker processing
- queue backlog
- integrations
- error rate
- latency
- critical user journeys

### 25.4 Rollback

Rollback procedures must distinguish:

- application rollback
- worker rollback
- configuration rollback
- integration disable
- database recovery

Database rollback must never be assumed safe without migration-specific planning.

## 26. BACKUP AND RECOVERY

### 26.1 Backup scope

Backups must cover:

- PostgreSQL data
- storage objects or recoverable storage strategy
- critical configuration
- migration history
- infrastructure configuration where practical

### 26.2 Backup controls

- automated schedule
- monitored success
- protected access
- documented retention
- separate failure alert
- periodic restore test

### 26.3 Recovery objectives

Final recovery point and recovery time objectives must be formally approved before production launch.

Do not invent them as dummy values.

### 26.4 Restore testing

A backup is not considered reliable until restoration has been tested.

Restore tests must verify:

- database integrity
- application compatibility
- permissions
- critical records
- file references
- audit history

## 27. DISASTER RECOVERY

Disaster scenarios include:

- accidental data deletion
- failed migration
- compromised credentials
- database outage
- storage outage
- deployment corruption
- provider outage
- widespread worker failure

The recovery plan must define:

- incident owner
- containment
- service restoration
- data restoration
- credential rotation
- customer or staff communication where required
- post-incident review

## 28. INCIDENT RESPONSE

### 28.1 Incident severity

Suggested severity classes:

- SEV-1: major security breach, critical data loss, or complete production outage
- SEV-2: significant degradation or high-risk security issue
- SEV-3: limited operational issue with workaround
- SEV-4: low-impact defect or warning

Final operational escalation details must be approved, not invented.

### 28.2 Incident lifecycle

1. detect
2. assess
3. contain
4. preserve evidence
5. remediate
6. recover
7. communicate
8. review
9. track preventive actions

### 28.3 Security incident controls

- revoke compromised credentials
- disable affected integration or account
- preserve logs
- restrict access
- identify affected data
- document timeline
- perform root-cause analysis
- update controls and tests

### 28.4 Post-incident review

Review must be blame-aware but focused on system improvement.

It should record:

- impact
- timeline
- root cause
- detection gap
- response effectiveness
- corrective work
- owner and due date

## 29. PRIVACY AND RETENTION

The system must support documented policies for:

- customer contact data
- communication history
- order history
- reservation history
- loyalty transactions
- staff records
- supplier records
- audit logs
- webhook payloads
- generated exports
- uploaded files
- AI request metadata

Retention automation must not delete records required for financial, legal, audit, or operational history.

## 30. QUALITY METRICS

Track quality signals such as:

- escaped defect count
- regression count
- test pass rate
- flaky test rate
- build failure rate
- deployment failure rate
- change failure rate
- mean time to recovery
- p95 API latency
- slow query count
- error rate
- accessibility issue count
- security finding age
- dependency vulnerability age
- backup success rate
- restore-test status

Metrics are used for improvement, not to hide defects through selective reporting.

## 31. PRODUCTION READINESS CHECKLIST

Before production launch:

- architecture reviewed
- database migrations validated
- authentication configured
- permissions tested
- secrets stored securely
- production CORS configured
- secure cookies enabled
- CSRF strategy implemented
- security headers configured
- rate limits enabled
- file validation and scanning configured
- webhook verification implemented
- idempotency tested
- audit logging active
- structured logging active
- Sentry active
- alerts configured
- health checks configured
- backups enabled
- restore test completed
- dependency scans clean or approved
- critical E2E tests passing
- performance test completed (k6)
- accessibility review completed
- rollback plan documented
- incident contacts approved
- production integrations validated
- no dummy credentials or production URLs
- no test bypasses

## 32. DEFINITION OF DONE

A feature is complete only when:

- business behavior matches the relevant module document
- data and API behavior match `DATABASE_AND_API.md`
- architecture matches `ARCHITECTURE_AND_TECH_STACK.md`
- integration behavior matches `INTEGRATIONS_AUTOMATIONS_REALTIME.md`
- backend authorization is enforced using the canonical capability registry
- validation exists
- database constraints exist where appropriate
- audit behavior exists for sensitive actions
- logging and observability exist
- loading, empty, error, disabled, and degraded UI states exist
- automated tests cover success and failure paths
- security tests cover relevant threats
- performance is measured for high-impact paths
- documentation is updated
- no dummy critical decision is introduced
- CI passes
- staging validation succeeds

## 33. FINAL IMPLEMENTATION COMMAND

Build and operate the RKPR Restaurant CRM as a secure, observable, performant, and production-quality system. Enforce authentication and capability-based authorization in the backend, protect secrets and sensitive data, validate every external input, secure files and webhooks, use private-by-default storage, preserve immutable financial and operational history, and maintain complete auditability for consequential actions. Design for bounded queries, asynchronous heavy work (ARQ), graceful degradation, independent worker scaling, and measurable performance (k6). Require automated testing, security checks, migration validation, vulnerability scanning, backups, restore tests, monitoring, alerting, incident response, and release gates before production. Preserve established RKPR dummy records only for development and tests; never invent credentials, providers, production URLs, recovery objectives, legal requirements, or critical security decisions.
